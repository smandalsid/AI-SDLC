"""The proposed action: INV-1 to INV-8 and the per-intent required fields (AC-12)."""

import pytest
from app_helpers import action_dict, create_dict
from pydantic import ValidationError

from app.models.action import ProposedAction, ProposedActionWire

pytestmark = pytest.mark.covers(
    "INV-1", "INV-2", "INV-3", "INV-4", "INV-6", "INV-7", "INV-8", "AC-12", "FR-2"
)

FIELDS = {
    "intent",
    "title",
    "datetime_iso",
    "snooze_minutes",
    "target_reminder_id",
    "clarification_question",
    "refusal_reason",
    "confidence",
}


def _snooze(**overrides: object) -> dict[str, object]:
    base = action_dict(
        intent="snooze",
        target_reminder_id="r1",
        snooze_minutes=60,
        clarification_question=None,
    )
    return {**base, **overrides}


def _ok(data: dict[str, object]) -> bool:
    try:
        ProposedAction.model_validate(data)
    except ValidationError:
        return False
    return True


def test_wire_model_has_exactly_the_eight_required_fields() -> None:
    assert set(ProposedActionWire.model_fields) == FIELDS
    assert all(f.is_required() for f in ProposedActionWire.model_fields.values())


def test_wire_model_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProposedActionWire.model_validate({**action_dict(), "extra": 1})


def test_valid_action_for_every_intent() -> None:
    valid = [
        action_dict(),
        create_dict(),
        action_dict(
            intent="reschedule",
            datetime_iso="2026-11-06T16:00:00+00:00",
            target_reminder_id="r1",
            clarification_question=None,
        ),
        _snooze(),
        action_dict(intent="cancel", target_reminder_id="r1", clarification_question=None),
        action_dict(intent="refuse", refusal_reason="injection", clarification_question=None),
    ]
    assert all(_ok(v) for v in valid)


def test_unknown_intent_and_extra_field_are_rejected() -> None:
    assert not _ok(action_dict(intent="delete"))
    assert not _ok({**action_dict(), "extra": 1})


@pytest.mark.parametrize(("minutes", "ok"), [(0, False), (1, True), (1440, True), (1441, False)])
def test_snooze_minutes_range(minutes: int, ok: bool) -> None:
    assert _ok(_snooze(snooze_minutes=minutes)) is ok


def test_snooze_minutes_must_be_an_integer() -> None:
    assert not _ok(_snooze(snooze_minutes="60"))
    assert not _ok(_snooze(snooze_minutes=60.5))


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("2026-11-09T09:00:00+05:30", True),
        ("2026-11-09T09:00:00Z", True),
        ("2026-11-09T09:00:00", False),
        ("2026-11-09 09:00:00+00:00", False),
        ("tomorrow", False),
    ],
)
def test_datetime_needs_an_explicit_utc_offset(value: str, ok: bool) -> None:
    assert _ok(create_dict(datetime_iso=value)) is ok


@pytest.mark.parametrize(("length", "ok"), [(0, False), (1, True), (120, True), (121, False)])
def test_title_length(length: int, ok: bool) -> None:
    assert _ok(create_dict(title="x" * length)) is ok


@pytest.mark.parametrize(("length", "ok"), [(0, False), (1, True), (200, True), (201, False)])
def test_clarification_question_length(length: int, ok: bool) -> None:
    assert _ok(action_dict(clarification_question="x" * length)) is ok


def test_question_only_for_clarify_and_required_for_clarify() -> None:
    assert not _ok(create_dict(clarification_question="when?"))
    assert not _ok(action_dict(clarification_question=None))


def test_reason_only_for_refuse_and_required_for_refuse() -> None:
    assert not _ok(create_dict(refusal_reason="unsafe"))
    assert not _ok(action_dict(intent="refuse", clarification_question=None))
    assert not _ok(action_dict(intent="refuse", refusal_reason="rude", clarification_question=None))


@pytest.mark.parametrize(("confidence", "ok"), [(0, True), (1, True), (1.01, False), (-0.1, False)])
def test_confidence_range(confidence: float, ok: bool) -> None:
    assert _ok(action_dict(confidence=confidence)) is ok


@pytest.mark.parametrize(
    "data",
    [
        create_dict(title=None),
        create_dict(datetime_iso=None),
        action_dict(
            intent="reschedule", datetime_iso="2026-11-06T16:00:00Z", clarification_question=None
        ),
        action_dict(intent="reschedule", target_reminder_id="r1", clarification_question=None),
        _snooze(target_reminder_id=None),
        _snooze(snooze_minutes=None),
        action_dict(intent="cancel", clarification_question=None),
    ],
)
def test_missing_required_field_per_intent_is_rejected(data: dict[str, object]) -> None:
    assert not _ok(data)


def test_fields_an_intent_does_not_need_may_be_populated() -> None:
    assert _ok(create_dict(target_reminder_id="r1"))
