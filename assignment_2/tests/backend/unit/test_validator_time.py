"""Time rules for create and reschedule: future, zone offset, existing wall time (GR-5)."""

from collections.abc import Callable

import pytest
from app_helpers import NOW, action_dict, create_dict, request

from app.models.action import ProposedAction
from app.models.errors import LLMOutputError
from app.models.requests import CallerContext
from app.services.validator import default_rules, run_rules

pytestmark = pytest.mark.covers("FR-1", "FR-4", "GR-5", "AC-1", "AC-2", "AC-24", "AC-25", "AC-26")

NOW_ISO = "2026-11-05T10:00:00+00:00"
KOLKATA_NOW = "2026-11-05T10:00:00+05:30"
NEW_YORK_BEFORE_SPRING = "2027-03-13T12:00:00-05:00"
NEW_YORK_BEFORE_FALL = "2026-10-31T12:00:00-04:00"
R1 = {"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+00:00"}


def _check(action: dict[str, object], now: str = NOW_ISO, timezone: str = "UTC") -> None:
    req = request(now=now, timezone=timezone, reminders=[R1])
    context = CallerContext.build(req, NOW)
    run_rules(ProposedAction.model_validate(action), context, default_rules())


def _create(when: str) -> dict[str, object]:
    return create_dict(datetime_iso=when)


def _reschedule(when: str) -> dict[str, object]:
    return action_dict(
        intent="reschedule",
        target_reminder_id="r1",
        datetime_iso=when,
        clarification_question=None,
    )


def _reason(action: dict[str, object], now: str, timezone: str) -> str:
    with pytest.raises(LLMOutputError) as caught:
        _check(action, now, timezone)
    return caught.value.reason


Build = Callable[[str], dict[str, object]]
BUILD = pytest.mark.parametrize("build", [_create, _reschedule], ids=["create", "reschedule"])


@BUILD
@pytest.mark.parametrize(
    ("now", "timezone", "when"),
    [
        (KOLKATA_NOW, "Asia/Kolkata", "2026-11-09T09:00:00+05:30"),
        (NOW_ISO, "UTC", "2026-11-10T18:00:00+00:00"),
        (NOW_ISO, "UTC", "2026-11-10T18:00:00Z"),
        ("2026-11-05T23:50:00+00:00", "UTC", "2026-11-06T00:20:00+00:00"),
        ("2026-01-30T10:00:00+00:00", "UTC", "2026-02-02T09:00:00+00:00"),
        (NEW_YORK_BEFORE_SPRING, "America/New_York", "2027-03-14T09:00:00-04:00"),
        (NOW_ISO, "UTC", "2026-11-05T10:01:00+00:00"),
    ],
    ids=["AC-1", "AC-2", "utc-z", "AC-24", "AC-25", "AC-26", "now-plus-1-minute"],
)
def test_a_future_time_in_the_zone_offset_passes(
    build: Build, now: str, timezone: str, when: str
) -> None:
    _check(build(when), now, timezone)


@BUILD
@pytest.mark.parametrize(
    "when",
    [
        "2026-11-05T10:00:00+00:00",
        "2026-11-05T09:59:00+00:00",
        "2025-01-01T09:00:00+00:00",
    ],
    ids=["exactly-now", "one-minute-ago", "long-ago"],
)
def test_a_time_not_strictly_after_now_is_rejected(build: Build, when: str) -> None:
    assert _reason(build(when), NOW_ISO, "UTC") == "not_future"


def test_the_same_instant_written_in_the_zone_offset_is_still_now() -> None:
    reason = _reason(_create("2026-11-05T10:00:00+05:30"), KOLKATA_NOW, "Asia/Kolkata")
    assert reason == "not_future"


@BUILD
@pytest.mark.parametrize(
    ("now", "timezone", "when"),
    [
        (KOLKATA_NOW, "Asia/Kolkata", "2026-11-09T09:00:00+00:00"),
        (NOW_ISO, "UTC", "2026-11-10T18:00:00+01:00"),
        (NEW_YORK_BEFORE_SPRING, "America/New_York", "2027-03-14T09:00:00-05:00"),
    ],
    ids=["kolkata-written-as-utc", "utc-written-as-plus-1", "AC-26-stale-winter-offset"],
)
def test_an_offset_that_differs_from_the_zone_offset_is_rejected(
    build: Build, now: str, timezone: str, when: str
) -> None:
    assert _reason(build(when), now, timezone) == "offset_mismatch"


@BUILD
@pytest.mark.parametrize(
    ("now", "timezone", "when"),
    [
        (NEW_YORK_BEFORE_SPRING, "America/New_York", "2027-03-14T02:30:00-05:00"),
        (NEW_YORK_BEFORE_SPRING, "America/New_York", "2027-03-14T02:30:00-04:00"),
        (NEW_YORK_BEFORE_FALL, "America/New_York", "2026-11-01T01:30:00-04:00"),
        (NEW_YORK_BEFORE_FALL, "America/New_York", "2026-11-01T01:30:00-05:00"),
    ],
    ids=["AC-36-gap-winter", "AC-36-gap-summer", "ambiguous-first", "ambiguous-second"],
)
def test_a_wall_time_that_does_not_exist_or_occurs_twice_is_rejected(
    build: Build, now: str, timezone: str, when: str
) -> None:
    reason = _reason(build(when), now, timezone)
    assert reason == "nonexistent_or_ambiguous_time"


@pytest.mark.parametrize(
    "action",
    [
        action_dict(),
        action_dict(intent="refuse", refusal_reason="unsafe", clarification_question=None),
        action_dict(
            intent="snooze",
            target_reminder_id="r1",
            snooze_minutes=15,
            clarification_question=None,
        ),
        action_dict(intent="cancel", target_reminder_id="r1", clarification_question=None),
    ],
    ids=["clarify", "refuse", "snooze", "cancel"],
)
def test_intents_without_a_proposed_time_are_not_time_checked(action: dict[str, object]) -> None:
    _check(action)
