"""FR-8 length guard: over 1000 characters is refused before the model or prompt (AC-14, AC-16)."""

import pytest
from app_helpers import FixedClock, action_dict, request

from app.llm.stub_client import StubLLMClient
from app.models.action import Intent, RefusalReason
from app.services import interpreter as interpreter_module
from app.services.applier import Applier
from app.services.interpreter import Interpreter
from app.services.store import InMemoryReminderStore
from app.services.text_guard import MAX_TEXT_CHARS, refusal_for
from app.services.validator import default_rules

pytestmark = pytest.mark.covers("FR-8", "AC-14", "AC-16")

R1 = {"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+00:00"}


def _interpreter(stub: StubLLMClient) -> Interpreter:
    return Interpreter(
        stub, FixedClock(), Applier(), default_rules(), "RULES", InMemoryReminderStore
    )


def test_the_limit_is_1000_characters() -> None:
    assert MAX_TEXT_CHARS == 1000


@pytest.mark.parametrize("text", ["x" * 1000, "é" * 1000, "😀" * 1000, "x"])
def test_up_to_1000_characters_is_not_refused(text: str) -> None:
    assert refusal_for(text) is None


@pytest.mark.parametrize("text", ["x" * 1001, "é" * 1001, "😀" * 1001, " " * 1001])
def test_length_is_counted_in_characters_not_bytes(text: str) -> None:
    action = refusal_for(text)
    assert action is not None
    assert action.intent is Intent.refuse and action.refusal_reason is RefusalReason.too_long
    assert action.confidence == 1.0
    assert action.title is None and action.datetime_iso is None
    assert action.snooze_minutes is None and action.target_reminder_id is None
    assert action.clarification_question is None


async def test_ac_14_a_1001_character_text_never_reaches_the_model() -> None:
    stub = StubLLMClient(action_dict())
    response = await _interpreter(stub).interpret(request("x" * 1001, reminders=[R1]))
    assert stub.calls == 0
    assert response.action.intent is Intent.refuse
    assert response.action.refusal_reason is RefusalReason.too_long
    assert response.applied.operation == "none"
    assert [r.id for r in response.applied.reminders] == ["r1"]


async def test_ac_16_exactly_1000_characters_is_processed() -> None:
    stub = StubLLMClient(action_dict())
    text = "remind me to " + "x" * 987
    assert len(text) == 1000
    response = await _interpreter(stub).interpret(request(text))
    assert stub.calls == 1 and response.action.intent is Intent.clarify


async def test_the_check_runs_before_the_prompt_is_built(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("prompt built for a rejected text")

    monkeypatch.setattr(interpreter_module, "build_prompt", forbidden)
    stub = StubLLMClient(action_dict())
    response = await _interpreter(stub).interpret(request("x" * 1001))
    assert response.action.refusal_reason is RefusalReason.too_long and stub.calls == 0
