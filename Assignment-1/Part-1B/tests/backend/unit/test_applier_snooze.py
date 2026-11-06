"""SnoozeHandler: target time plus the duration, or now plus the duration once passed (FR-6)."""

from datetime import datetime

import pytest
from app_helpers import NOW, action_dict, request

from app.models.action import ProposedAction
from app.models.requests import CallerContext
from app.services.applier import Applier, SnoozeHandler
from app.services.store import InMemoryReminderStore, Reminder

pytestmark = pytest.mark.covers("FR-6", "INV-4", "AC-20", "AC-21")

NEW_YORK_NOW = "2027-03-13T12:00:00-05:00"
R_OTHER = Reminder("r9", "Gym session", datetime.fromisoformat("2026-11-07T07:00:00+00:00"))


def _reminder(time: str, rid: str = "r3") -> Reminder:
    return Reminder(rid, "Call vendor", datetime.fromisoformat(time))


def _snooze(minutes: int, target: str = "r3") -> ProposedAction:
    return ProposedAction.model_validate(
        action_dict(
            intent="snooze",
            target_reminder_id=target,
            snooze_minutes=minutes,
            clarification_question=None,
        )
    )


def _context(timezone: str = "UTC", now: str | None = None) -> CallerContext:
    req = request(timezone=timezone) if now is None else request(timezone=timezone, now=now)
    return CallerContext.build(req, NOW)


@pytest.mark.parametrize(
    ("target_time", "minutes", "expected"),
    [
        ("2026-11-05T11:00:00+00:00", 120, "2026-11-05T13:00:00+00:00"),
        ("2026-11-05T09:00:00+00:00", 15, "2026-11-05T10:15:00+00:00"),
        ("2026-11-05T10:00:00+00:00", 15, "2026-11-05T10:15:00+00:00"),
        ("2026-11-05T10:00:01+00:00", 15, "2026-11-05T10:15:01+00:00"),
        ("2026-11-05T09:59:59+00:00", 15, "2026-11-05T10:15:00+00:00"),
        ("2026-11-05T11:00:00+00:00", 1, "2026-11-05T11:01:00+00:00"),
        ("2026-11-05T11:00:00+00:00", 1440, "2026-11-06T11:00:00+00:00"),
        ("2026-11-04T09:00:00+00:00", 1440, "2026-11-06T10:00:00+00:00"),
    ],
    ids=["AC-20", "AC-21", "equal-to-now", "just-future", "just-passed", "1", "1440", "stale-1440"],
)
def test_the_new_time_follows_the_two_branches_of_fr_6(
    target_time: str, minutes: int, expected: str
) -> None:
    store = InMemoryReminderStore([_reminder(target_time), R_OTHER])
    result = Applier().apply(_snooze(minutes), store, _context())
    assert result.operation == "snoozed" and result.affected_id == "r3"
    assert result.new_time == expected
    assert {r.id: r.time.isoformat() for r in store.list()}["r3"] == expected


def test_only_the_target_changes_and_its_title_stays() -> None:
    store = InMemoryReminderStore([_reminder("2026-11-05T11:00:00+00:00"), R_OTHER])
    result = Applier().apply(_snooze(30), store, _context())
    by_id = {r.id: r for r in store.list()}
    assert by_id["r3"].title == "Call vendor" and by_id["r9"] == R_OTHER and len(by_id) == 2
    assert {r.id: r.time for r in result.reminders} == {
        "r3": "2026-11-05T11:30:00+00:00",
        "r9": "2026-11-07T07:00:00+00:00",
    }


def test_the_result_is_expressed_in_the_callers_zone() -> None:
    store = InMemoryReminderStore([_reminder("2026-11-05T11:00:00+00:00")])
    result = Applier().apply(_snooze(120), store, _context("Asia/Kolkata"))
    assert result.new_time == "2026-11-05T18:30:00+05:30"


def test_a_snooze_across_a_daylight_saving_change_keeps_elapsed_minutes_exact() -> None:
    store = InMemoryReminderStore([_reminder("2027-03-14T01:30:00-05:00")])
    result = Applier().apply(_snooze(120), store, _context("America/New_York", NEW_YORK_NOW))
    assert result.new_time == "2027-03-14T04:30:00-04:00"


def test_a_passed_target_in_a_dst_zone_snoozes_from_now_by_elapsed_minutes() -> None:
    store = InMemoryReminderStore([_reminder("2027-03-13T08:00:00-05:00")])
    now = "2027-03-14T01:30:00-05:00"
    result = Applier().apply(_snooze(60), store, _context("America/New_York", now))
    assert result.new_time == "2027-03-14T03:30:00-04:00"


def test_the_handler_reports_the_change_it_made() -> None:
    store = InMemoryReminderStore([_reminder("2026-11-05T11:00:00+00:00")])
    change = SnoozeHandler().handle(_snooze(120), store, _context())
    assert change.operation == "snoozed" and change.affected_id == "r3"
    assert change.new_time == datetime.fromisoformat("2026-11-05T13:00:00+00:00")
