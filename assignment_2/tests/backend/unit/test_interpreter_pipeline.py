"""One request through the pipeline: validate, never trust, apply nothing on failure."""

import pytest
from app_helpers import FixedClock, action_dict, create_dict, request

from app.llm.protocol import LLMResult
from app.llm.stub_client import StubLLMClient
from app.models.action import ProposedAction
from app.models.errors import LLMInfrastructureError, LLMOutputError
from app.models.requests import CallerContext, InterpretRequest
from app.models.responses import AppliedResult
from app.services.applier import Applier, UnregisteredIntentError
from app.services.interpreter import Interpreter
from app.services.store import ReminderStore
from app.services.validator import default_rules

pytestmark = pytest.mark.covers("GR-5", "INV-5", "INV-1", "AC-12")

R1 = {"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+00:00"}


class SpyApplier:
    def __init__(self) -> None:
        self.calls = 0

    def apply(
        self, action: ProposedAction, store: ReminderStore, context: CallerContext
    ) -> AppliedResult:
        self.calls += 1
        return Applier().apply(action, store, context)


def _interpreter(stub: StubLLMClient, applier: SpyApplier | Applier | None = None) -> Interpreter:
    return Interpreter(stub, FixedClock(), applier or Applier(), default_rules(), "RULES")


async def test_clarify_and_refuse_pass_through_without_changing_anything() -> None:
    for scripted in (
        action_dict(),
        action_dict(intent="refuse", refusal_reason="injection", clarification_question=None),
    ):
        response = await _interpreter(StubLLMClient(scripted)).interpret(request(reminders=[R1]))
        assert response.applied.operation == "none" and response.applied.affected_id is None
        assert [r.id for r in response.applied.reminders] == ["r1"]
        assert response.action.intent == scripted["intent"]


async def test_the_prompt_sent_to_the_model_carries_the_request_data() -> None:
    stub = StubLLMClient(action_dict())
    await _interpreter(stub).interpret(request("remind me to pay rent"))
    sent = stub.requests[0]
    assert "remind me to pay rent" in sent.user_message and sent.system_prompt.startswith("RULES")
    assert sent.correlation_id


async def test_a_target_outside_the_supplied_list_is_rejected_and_nothing_is_applied() -> None:
    spy = SpyApplier()
    stub = StubLLMClient(
        action_dict(intent="cancel", target_reminder_id="zz", clarification_question=None)
    )
    with pytest.raises(LLMOutputError) as info:
        await _interpreter(stub, spy).interpret(request(reminders=[R1]))
    assert info.value.reason == "unknown_target" and spy.calls == 0


async def test_output_failing_the_domain_schema_is_rejected() -> None:
    spy = SpyApplier()
    stub = StubLLMClient(
        action_dict(
            intent="snooze", target_reminder_id="r1", snooze_minutes=0, clarification_question=None
        )
    )
    with pytest.raises(LLMOutputError) as info:
        await _interpreter(stub, spy).interpret(request(reminders=[R1]))
    assert info.value.reason == "schema" and spy.calls == 0


async def test_model_output_error_and_infrastructure_error_propagate() -> None:
    with pytest.raises(LLMOutputError):
        await _interpreter(StubLLMClient(LLMOutputError("schema", "bad"))).interpret(request())
    with pytest.raises(LLMInfrastructureError):
        await _interpreter(StubLLMClient(LLMInfrastructureError("timeout", "slow"))).interpret(
            request()
        )


async def test_an_intent_without_a_registered_handler_is_a_programming_error() -> None:
    stub = StubLLMClient(create_dict())
    with pytest.raises(UnregisteredIntentError):
        await _interpreter(stub, Applier({})).interpret(request())


async def test_the_default_now_comes_from_the_injected_clock() -> None:
    stub = StubLLMClient(action_dict())
    await _interpreter(stub).interpret(InterpretRequest.model_validate({"text": "remind me"}))
    assert "2026-11-05T10:00:00+00:00" in stub.requests[0].system_prompt


def test_llm_result_pairs_the_wire_action_with_the_call_record() -> None:
    assert {"wire", "record"} <= set(LLMResult.__dataclass_fields__)
