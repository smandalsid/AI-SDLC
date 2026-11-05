"""GR-5, INV-5: untrusted output gives a controlled error and applies nothing."""

import pytest
from app_helpers import FixedClock, action_dict, create_dict, request

from app.llm.protocol import LLMRequest
from app.llm.stub_client import StubLLMClient
from app.models.action import ProposedAction
from app.models.errors import LLMOutputError
from app.models.requests import CallerContext
from app.models.responses import AppliedResult
from app.services.applier import Applier
from app.services.interpreter import Interpreter
from app.services.store import ReminderStore
from app.services.validator import default_rules

pytestmark = pytest.mark.covers("GR-5", "INV-5", "INV-8", "AC-12")

R1 = {"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+00:00"}


class SpyApplier:
    def __init__(self) -> None:
        self.calls = 0

    def apply(
        self, action: ProposedAction, store: ReminderStore, context: CallerContext
    ) -> AppliedResult:
        self.calls += 1
        return Applier().apply(action, store, context)


def _without(field: str) -> dict[str, object]:
    scripted = create_dict()
    del scripted[field]
    return scripted


BAD_OUTPUTS: dict[str, dict[str, object]] = {
    "extra-field": {**create_dict(), "run": "rm -rf /"},
    "unknown-target": action_dict(
        intent="cancel", target_reminder_id="zz", clarification_question=None
    ),
    "snooze-too-small": action_dict(
        intent="snooze", target_reminder_id="r1", snooze_minutes=0, clarification_question=None
    ),
    "snooze-too-large": action_dict(
        intent="snooze", target_reminder_id="r1", snooze_minutes=1441, clarification_question=None
    ),
    "confidence-out-of-range": create_dict(confidence=1.5),
    "intent-not-allowed": create_dict(intent="delete_all"),
    "naive-datetime": create_dict(datetime_iso="2026-11-09T09:00:00"),
    "missing-required-field": _without("confidence"),
    "missing-title-for-create": create_dict(title=None),
    "clarify-without-question": action_dict(clarification_question=None),
}


@pytest.mark.parametrize("scripted", BAD_OUTPUTS.values(), ids=BAD_OUTPUTS.keys())
async def test_a_bad_output_is_a_controlled_error_and_nothing_is_applied(
    scripted: dict[str, object],
) -> None:
    spy = SpyApplier()
    interpreter = Interpreter(StubLLMClient(scripted), FixedClock(), spy, default_rules(), "RULES")
    with pytest.raises(LLMOutputError):
        await interpreter.interpret(request(reminders=[R1]))
    assert spy.calls == 0


async def test_the_stub_reports_a_bad_wire_shape_like_the_real_clients() -> None:
    with pytest.raises(LLMOutputError) as caught:
        await StubLLMClient(BAD_OUTPUTS["extra-field"]).parse(LLMRequest("s", "u", "c"))
    assert caught.value.reason == "schema"
