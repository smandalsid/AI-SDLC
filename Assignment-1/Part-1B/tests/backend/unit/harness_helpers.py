"""Builders shared by the harness unit tests."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from evaluators.common import JSON, CheckResult, Observation

ROOT = Path(__file__).resolve().parents[3]


def thresholds_env() -> dict[str, str]:
    """Parse the protected thresholds file so tests never duplicate its numbers."""
    env: dict[str, str] = {}
    for raw in (ROOT / ".harness/config/thresholds.env").read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            env[key] = value
    return env


def make_case(
    case_id: str = "N01",
    category: str = "normal",
    *,
    text: JSON = "remind me to pay rent",
    timezone: str = "UTC",
    now: str = "2026-11-05T10:00:00+00:00",
    reminders: list[JSON] | None = None,
    traces: tuple[str, ...] = ("AC-1", "FR-1"),
    expected: JSON | None = None,
    consistency: bool = False,
) -> JSON:
    return {
        "id": case_id,
        "category": category,
        "consistency": consistency,
        "traces": list(traces),
        "input": {
            "text": text,
            "timezone": timezone,
            "now": now,
            "reminders": reminders or [],
        },
        "expected": expected if expected is not None else {"intent": "create"},
    }


def make_action(**overrides: JSON) -> JSON:
    base: JSON = {
        "intent": "create",
        "title": "pay rent",
        "datetime_iso": "2026-11-09T09:00:00+00:00",
        "snooze_minutes": None,
        "target_reminder_id": None,
        "clarification_question": None,
        "refusal_reason": None,
        "confidence": 0.9,
    }
    return {**base, **overrides}


def make_applied(
    operation: str = "none",
    affected_id: str | None = None,
    new_time: str | None = None,
    reminders: list[JSON] | None = None,
) -> JSON:
    return {
        "operation": operation,
        "affected_id": affected_id,
        "new_time": new_time,
        "reminders": reminders or [],
    }


def make_reminder(
    rid: str, title: str = "Dentist", time: str = "2026-11-06T10:00:00+00:00"
) -> JSON:
    return {"id": rid, "title": title, "time": time}


def make_obs(
    action: JSON | None = None,
    *,
    status: int = 200,
    applied: JSON | None = None,
    model_calls: int = 1,
    infra_kind: str | None = None,
    call: JSON | None = None,
) -> Observation:
    return Observation(
        status_code=status,
        action=action,
        applied=applied,
        model_calls=model_calls,
        infra_kind=infra_kind,
        call=call,
    )


def passed_map(results: Sequence[CheckResult]) -> dict[str, bool]:
    """Map check_id to passed for assertions."""
    return {r.check_id: r.passed for r in results}
