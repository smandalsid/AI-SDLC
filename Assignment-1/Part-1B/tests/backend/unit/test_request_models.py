"""Request models: reminders, timezone, now, extra fields (FR-8 support, INV-5 support)."""

import pytest
from pydantic import ValidationError

from app.models.requests import InterpretRequest, ReminderIn

pytestmark = pytest.mark.covers("FR-8", "FR-1")


def _reminder(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+00:00"}
    return {**base, **overrides}


@pytest.mark.parametrize(
    ("rid", "ok"),
    [
        ("r1", True),
        ("a_B-9", True),
        ("x" * 64, True),
        ("", False),
        ("x" * 65, False),
        ("a b", False),
        ("é", False),
    ],
)
def test_reminder_id_pattern_and_length(rid: str, ok: bool) -> None:
    if ok:
        ReminderIn.model_validate(_reminder(id=rid))
    else:
        with pytest.raises(ValidationError):
            ReminderIn.model_validate(_reminder(id=rid))


@pytest.mark.parametrize(("length", "ok"), [(0, False), (1, True), (120, True), (121, False)])
def test_reminder_title_length(length: int, ok: bool) -> None:
    if ok:
        ReminderIn.model_validate(_reminder(title="x" * length))
    else:
        with pytest.raises(ValidationError):
            ReminderIn.model_validate(_reminder(title="x" * length))


def test_reminder_time_must_carry_an_offset_and_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ReminderIn.model_validate(_reminder(time="2026-11-06T10:00:00"))
    with pytest.raises(ValidationError):
        ReminderIn.model_validate({**_reminder(), "extra": 1})


def test_request_defaults() -> None:
    request = InterpretRequest.model_validate({"text": "remind me"})
    assert request.timezone == "UTC" and request.now is None and request.reminders == []


def test_unknown_timezone_is_invalid_never_a_silent_fallback() -> None:
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": "x", "timezone": "Mars/Phobos"})
    InterpretRequest.model_validate({"text": "x", "timezone": "Asia/Kolkata"})


def test_now_must_carry_an_offset() -> None:
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": "x", "now": "2026-11-05T10:00:00"})
    InterpretRequest.model_validate({"text": "x", "now": "2026-11-05T10:00:00+05:30"})


@pytest.mark.parametrize("text", [5, None, ["a"], {"a": 1}])
def test_text_must_be_a_string(text: object) -> None:
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": text})


def test_reminder_list_is_capped_and_ids_are_unique() -> None:
    many = [_reminder(id=f"r{i}") for i in range(201)]
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": "x", "reminders": many})
    InterpretRequest.model_validate({"text": "x", "reminders": many[:200]})
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": "x", "reminders": [_reminder(), _reminder()]})


def test_unknown_request_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": "x", "mode": "admin"})
