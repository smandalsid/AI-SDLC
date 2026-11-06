"""Builders shared by the application tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models.requests import InterpretRequest, ReminderIn

JsonObject = dict[str, Any]  # parsed JSON has no static type
NOW = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
NOW_ISO = "2026-11-05T10:00:00+00:00"


class FixedClock:
    def __init__(self, now: datetime = NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def action_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "intent": "clarify",
        "title": None,
        "datetime_iso": None,
        "snooze_minutes": None,
        "target_reminder_id": None,
        "clarification_question": "What time?",
        "refusal_reason": None,
        "confidence": 0.9,
    }
    return {**base, **overrides}


def create_dict(**overrides: object) -> dict[str, object]:
    base = action_dict(
        intent="create",
        title="pay rent",
        datetime_iso="2026-11-09T09:00:00+00:00",
        clarification_question=None,
    )
    return {**base, **overrides}


def reminder(
    rid: str, title: str = "Dentist", time: str = "2026-11-06T10:00:00+00:00"
) -> ReminderIn:
    return ReminderIn(id=rid, title=title, time=datetime.fromisoformat(time))


def request(text: str = "remind me", **overrides: object) -> InterpretRequest:
    fields: dict[str, object] = {"text": text, "now": NOW_ISO, **overrides}
    return InterpretRequest.model_validate(fields)
