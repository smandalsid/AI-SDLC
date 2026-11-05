"""Deterministic calendar facts for the prompt: dates, offsets, daylight-saving changes (FR-1)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

Status = Literal["exists", "gap", "ambiguous"]
HORIZON_DAYS = 14


def _format_offset(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    hours, rest = divmod(abs(minutes), 60)
    return f"{'+' if minutes >= 0 else '-'}{hours:02d}:{rest:02d}"


def local_time_status(zone: ZoneInfo, naive_local: datetime) -> Status:
    """Whether a wall-clock time exists once, falls in a gap, or occurs twice in the zone."""
    first = naive_local.replace(tzinfo=zone, fold=0)
    round_trip = first.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
    if round_trip != naive_local:
        return "gap"
    second = naive_local.replace(tzinfo=zone, fold=1)
    return "ambiguous" if first.utcoffset() != second.utcoffset() else "exists"


def _offset_at(zone: ZoneInfo, day: date, at: time) -> timedelta:
    return datetime.combine(day, at, tzinfo=zone).utcoffset() or timedelta(0)


def _minute_label(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _transition_line(zone: ZoneInfo, day: date) -> str | None:
    before = _offset_at(zone, day, time(0, 0))
    after = _offset_at(zone, day, time(23, 59))
    if before == after:
        return None
    wanted: Status = "gap" if after > before else "ambiguous"
    minutes = [
        m
        for m in range(24 * 60)
        if local_time_status(zone, datetime.combine(day, time(m // 60, m % 60))) == wanted
    ]
    verb = "do not exist" if wanted == "gap" else "occur twice"
    window = f"{_minute_label(minutes[0])}-{_minute_label(minutes[-1])}"
    change = f"{_format_offset(before)} -> {_format_offset(after)}"
    return f"{day.isoformat()}: offset changes {change}; local times {window} {verb}"


def reference_calendar(zone: ZoneInfo, now: datetime) -> str:
    local = now.astimezone(zone)
    lines = [
        f"Local now: {local.isoformat()} ({local:%A}), timezone {zone}",
        f"Next {HORIZON_DAYS} local dates (date weekday UTC-offset):",
    ]
    changes: list[str] = []
    for step in range(1, HORIZON_DAYS + 1):
        day = local.date() + timedelta(days=step)
        offset = _format_offset(_offset_at(zone, day, time(12, 0)))
        lines.append(f"{day.isoformat()} {day:%A} {offset}")
        line = _transition_line(zone, day)
        if line:
            changes.append(line)
    return "\n".join(lines + changes)
