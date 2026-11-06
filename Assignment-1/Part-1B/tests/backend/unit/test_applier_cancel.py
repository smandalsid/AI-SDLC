"""CancelHandler: exactly the target is removed (FR-7)."""

from datetime import datetime

import pytest
from app_helpers import NOW, action_dict, request

from app.models.action import ProposedAction, ProposedActionWire
from app.models.requests import CallerContext
from app.services.applier import Applier, CancelHandler
from app.services.store import InMemoryReminderStore, Reminder

pytestmark = pytest.mark.covers("FR-7", "AC-22", "AC-23")

R1 = Reminder("r1", "Dentist appointment", datetime.fromisoformat("2026-11-06T10:00:00+00:00"))
R2 = Reminder("r2", "Gym session", datetime.fromisoformat("2026-11-07T07:00:00+00:00"))
R3 = Reminder("r3", "Call vendor", datetime.fromisoformat("2026-11-05T11:00:00+00:00"))
CONTEXT = CallerContext.build(request(), NOW)


def _cancel(target: str) -> ProposedAction:
    return ProposedAction.model_validate(
        action_dict(intent="cancel", target_reminder_id=target, clarification_question=None)
    )


def test_ac_23_only_the_target_is_removed_and_the_other_is_unchanged() -> None:
    store = InMemoryReminderStore([R1, R2])
    result = Applier().apply(_cancel("r2"), store, CONTEXT)
    assert list(store.list()) == [R1]
    assert result.operation == "cancelled" and result.affected_id == "r2"
    assert result.new_time is None
    assert [(r.id, r.title, r.time) for r in result.reminders] == [
        ("r1", "Dentist appointment", "2026-11-06T10:00:00+00:00")
    ]


@pytest.mark.parametrize("target", ["r1", "r2", "r3"])
def test_exactly_one_reminder_goes_whichever_is_named(target: str) -> None:
    store = InMemoryReminderStore([R1, R2, R3])
    result = Applier().apply(_cancel(target), store, CONTEXT)
    remaining = {r.id for r in store.list()}
    assert remaining == {"r1", "r2", "r3"} - {target}
    assert {r.id for r in result.reminders} == remaining


def test_the_handler_reports_the_change_it_made() -> None:
    change = CancelHandler().handle(_cancel("r1"), InMemoryReminderStore([R1, R2]), CONTEXT)
    assert change.operation == "cancelled" and change.affected_id == "r1"
    assert change.new_time is None


def test_the_contract_has_one_target_field_so_a_multi_id_cancel_cannot_be_expressed() -> None:
    assert ProposedActionWire.model_fields["target_reminder_id"].annotation == (str | None)
