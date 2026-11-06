"""The one structured action the model may propose (spec INV-1 to INV-8)."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ISO_WITH_OFFSET = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?(Z|[+-][0-9]{2}:[0-9]{2})$"
)


class Intent(StrEnum):
    create = "create"
    reschedule = "reschedule"
    snooze = "snooze"
    cancel = "cancel"
    clarify = "clarify"
    refuse = "refuse"


class RefusalReason(StrEnum):
    unsafe = "unsafe"
    injection = "injection"
    out_of_scope = "out_of_scope"
    bulk_action = "bulk_action"
    too_long = "too_long"


REQUIRED_BY_INTENT: dict[Intent, tuple[str, ...]] = {
    Intent.create: ("title", "datetime_iso"),
    Intent.reschedule: ("target_reminder_id", "datetime_iso"),
    Intent.snooze: ("target_reminder_id", "snooze_minutes"),
    Intent.cancel: ("target_reminder_id",),
    Intent.clarify: ("clarification_question",),
    Intent.refuse: ("refusal_reason",),
}


class ProposedActionWire(BaseModel):
    """What the SDK is asked to return: plain types, all fields required."""

    model_config = ConfigDict(extra="forbid")

    intent: Literal["create", "reschedule", "snooze", "cancel", "clarify", "refuse"]
    title: str | None
    datetime_iso: str | None
    snooze_minutes: int | None
    target_reminder_id: str | None
    clarification_question: str | None
    refusal_reason: Literal["unsafe", "injection", "out_of_scope", "bulk_action", "too_long"] | None
    confidence: float


class ProposedAction(BaseModel):
    """The validated action: the spec's ranges and cross-field rules are enforced here."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent
    title: str | None = Field(min_length=1, max_length=120)
    datetime_iso: str | None
    snooze_minutes: Annotated[int, Field(strict=True, ge=1, le=1440)] | None
    target_reminder_id: str | None
    clarification_question: str | None = Field(min_length=1, max_length=200)
    refusal_reason: RefusalReason | None
    confidence: float = Field(ge=0, le=1)

    @field_validator("datetime_iso")
    @classmethod
    def _aware(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not ISO_WITH_OFFSET.match(value):
            raise ValueError("datetime_iso must be ISO-8601 with an explicit UTC offset")
        datetime.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def _cross_field_rules(self) -> Self:
        missing = [f for f in REQUIRED_BY_INTENT[self.intent] if getattr(self, f) is None]
        if missing:
            raise ValueError(f"{self.intent.value} requires {', '.join(missing)}")
        if (self.clarification_question is not None) != (self.intent is Intent.clarify):
            raise ValueError("clarification_question is present if and only if intent is clarify")
        if (self.refusal_reason is not None) != (self.intent is Intent.refuse):
            raise ValueError("refusal_reason is present if and only if intent is refuse")
        return self

    @classmethod
    def from_wire(cls, wire: ProposedActionWire) -> ProposedAction:
        return cls.model_validate(wire.model_dump())
