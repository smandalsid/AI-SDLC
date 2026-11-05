"""Request models and the per-call context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictStr, field_validator

MAX_REMINDERS = 200


class ReminderIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=120)
    time: AwareDatetime


class InterpretRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: StrictStr
    timezone: str = "UTC"
    now: AwareDatetime | None = None
    reminders: list[ReminderIn] = Field(default_factory=list, max_length=MAX_REMINDERS)

    @field_validator("timezone")
    @classmethod
    def _known_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"unknown timezone {value!r}") from error
        return value

    @field_validator("reminders")
    @classmethod
    def _unique_ids(cls, value: list[ReminderIn]) -> list[ReminderIn]:
        ids = [r.id for r in value]
        if len(ids) != len(set(ids)):
            raise ValueError("reminder ids must be unique")
        return value


@dataclass(frozen=True)
class CallerContext:
    zone: ZoneInfo
    now_utc: datetime
    now_local: datetime
    reminders: tuple[ReminderIn, ...]

    @classmethod
    def build(cls, request: InterpretRequest, clock_now: datetime) -> CallerContext:
        zone = ZoneInfo(request.timezone)
        now = request.now or clock_now
        return cls(zone, now.astimezone(UTC), now.astimezone(zone), tuple(request.reminders))
