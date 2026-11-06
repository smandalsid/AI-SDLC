"""RescheduleHandler: only the target's time changes (FR-5)."""

from datetime import datetime

import pytest
from app_helpers import NOW, action_dict, request

from app.models.action import ProposedAction
from app.models.requests import CallerContext
from app.services.applier import Applier, RescheduleHandler
from app.services.store import InMemoryReminderStore, Reminder

pytestmark = pytest.mark.covers("FR-5", "AC-17")

WHEN = "2026-11-06T16:00:00+00:00"
R1 = Reminder("r1", "Dentist appointment", datetime.fromisoformat("2026-11-06T10:00:00+00:00"))
R2 = Reminder("r2", "Gym session", datetime.fromisoformat("2026-11-07T07:00:00+00:00"))
CONTEXT = CallerContext.build(request(), NOW)


def _action(target: str = "r1") -> ProposedAction:
    return ProposedAction.model_validate(
        action_dict(
            intent="reschedule",
            target_reminder_id=target,
            datetime_iso=WHEN,
            clarification_question=None,
        )
    )


def test_only_the_target_time_changes_and_its_id_and_title_stay() -> None:
    store = InMemoryReminderStore([R1, R2])
    result = Applier().apply(_action(), store, CONTEXT)
    by_id = {r.id: r for r in store.list()}
    assert by_id["r1"] == Reminder("r1", "Dentist appointment", datetime.fromisoformat(WHEN))
    assert by_id["r2"] == R2 and len(by_id) == 2
    assert result.operation == "rescheduled" and result.affected_id == "r1"
    assert result.new_time == WHEN


def test_the_result_lists_the_new_time_and_leaves_the_other_reminder_alone() -> None:
    result = Applier().apply(_action("r2"), InMemoryReminderStore([R1, R2]), CONTEXT)
    listed = {r.id: (r.title, r.time) for r in result.reminders}
    assert listed == {
        "r1": ("Dentist appointment", "2026-11-06T10:00:00+00:00"),
        "r2": ("Gym session", WHEN),
    }


def test_the_handler_reports_the_change_it_made() -> None:
    change = RescheduleHandler().handle(_action(), InMemoryReminderStore([R1]), CONTEXT)
    assert change.operation == "rescheduled" and change.affected_id == "r1"
    assert change.new_time == datetime.fromisoformat(WHEN)
