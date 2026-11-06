"""Targets: reschedule, snooze and cancel need an id that exactly matches a supplied one (INV-5)."""

import pytest
from app_helpers import NOW, action_dict, request

from app.models.action import ProposedAction
from app.models.errors import LLMOutputError
from app.models.requests import CallerContext
from app.services.validator import default_rules, run_rules

pytestmark = pytest.mark.covers("INV-5", "FR-5", "FR-7", "GR-5", "AC-12", "AC-18")

R1 = {"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+00:00"}
R2 = {"id": "r2", "title": "Gym", "time": "2026-11-07T07:00:00+00:00"}
WHEN = "2026-11-06T16:00:00+00:00"

TARGETED: dict[str, dict[str, object]] = {
    "reschedule": {"datetime_iso": WHEN},
    "snooze": {"snooze_minutes": 15},
    "cancel": {},
}


def _action(intent: str, target: str | None) -> ProposedAction:
    fields = action_dict(
        intent=intent, target_reminder_id="r1", clarification_question=None, **TARGETED[intent]
    )
    action = ProposedAction.model_validate(fields)
    return action.model_copy(update={"target_reminder_id": target})


def _check(action: ProposedAction, *reminders: dict[str, str]) -> None:
    context = CallerContext.build(request(reminders=list(reminders)), NOW)
    run_rules(action, context, default_rules())


@pytest.mark.parametrize("intent", TARGETED)
@pytest.mark.parametrize("target", ["r1", "r2"])
def test_a_target_that_matches_a_supplied_id_passes(intent: str, target: str) -> None:
    _check(_action(intent, target), R1, R2)


@pytest.mark.parametrize("intent", TARGETED)
@pytest.mark.parametrize(
    "target",
    [None, "", "zz", "R1", "r1 ", " r1", "r", "r11", "rem-1"],
    ids=[
        "missing",
        "empty",
        "unknown",
        "case-changed",
        "trailing",
        "leading",
        "prefix",
        "longer",
        "minted",
    ],
)
def test_a_missing_unknown_or_altered_id_is_rejected(intent: str, target: str | None) -> None:
    with pytest.raises(LLMOutputError) as caught:
        _check(_action(intent, target), R1, R2)
    assert caught.value.reason == "unknown_target"


@pytest.mark.parametrize("intent", TARGETED)
def test_an_empty_reminder_list_has_no_valid_target(intent: str) -> None:
    with pytest.raises(LLMOutputError) as caught:
        _check(_action(intent, "r1"))
    assert caught.value.reason == "unknown_target"


def test_a_create_cannot_smuggle_in_an_id_of_its_own() -> None:
    action = ProposedAction.model_validate(
        action_dict(
            intent="create",
            title="pay rent",
            datetime_iso="2026-11-09T09:00:00+00:00",
            target_reminder_id="made-up",
            clarification_question=None,
        )
    )
    with pytest.raises(LLMOutputError) as caught:
        _check(action, R1)
    assert caught.value.reason == "unknown_target"
