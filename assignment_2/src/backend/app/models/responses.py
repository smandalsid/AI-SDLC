"""Response models returned to callers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.action import ProposedAction

Operation = Literal["created", "rescheduled", "snoozed", "cancelled", "none"]


class ReminderOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    time: str


class AppliedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Operation
    affected_id: str | None
    new_time: str | None
    reminders: list[ReminderOut]


class InterpretResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ProposedAction
    applied: AppliedResult
