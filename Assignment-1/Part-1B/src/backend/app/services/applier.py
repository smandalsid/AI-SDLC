"""Applies a validated action to the in-memory store through a registry of handlers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast

from app.models.action import Intent, ProposedAction
from app.models.requests import CallerContext
from app.models.responses import AppliedResult, Operation, ReminderOut
from app.services.store import ReminderStore


class UnregisteredIntentError(RuntimeError):
    """No handler is registered for an intent that passed validation: a programming error."""


@dataclass(frozen=True)
class Change:
    operation: Operation
    affected_id: str | None = None
    new_time: datetime | None = None


class ActionHandler(Protocol):
    def handle(
        self, action: ProposedAction, store: ReminderStore, context: CallerContext
    ) -> Change: ...


class ActionApplier(Protocol):
    def apply(
        self, action: ProposedAction, store: ReminderStore, context: CallerContext
    ) -> AppliedResult: ...


class NoopHandler:
    """clarify and refuse change nothing."""

    def handle(
        self, action: ProposedAction, store: ReminderStore, context: CallerContext
    ) -> Change:
        return Change("none")


class CreateHandler:
    """FR-1: adds one reminder; the id is minted by the store, never taken from the model."""

    def handle(
        self, action: ProposedAction, store: ReminderStore, context: CallerContext
    ) -> Change:
        # ProposedAction guarantees title and datetime_iso for create.
        when = datetime.fromisoformat(cast("str", action.datetime_iso))
        return Change("created", store.add(cast("str", action.title), when), when)


class RescheduleHandler:
    """FR-5: moves the target to the new time; its id and title stay."""

    def handle(
        self, action: ProposedAction, store: ReminderStore, context: CallerContext
    ) -> Change:
        # ProposedAction guarantees target and time here; the validator checked the id.
        target = cast("str", action.target_reminder_id)
        when = datetime.fromisoformat(cast("str", action.datetime_iso))
        store.set_time(target, when)
        return Change("rescheduled", target, when)


class SnoozeHandler:
    """FR-6: target time plus the duration, or now plus the duration once the target has passed."""

    def handle(
        self, action: ProposedAction, store: ReminderStore, context: CallerContext
    ) -> Change:
        target = cast("str", action.target_reminder_id)
        minutes = cast("int", action.snooze_minutes)
        current = next(r.time for r in store.list() if r.id == target)
        # UTC arithmetic: zone-aware addition would count wall-clock minutes across a DST change.
        base = max(current.astimezone(UTC), context.now_utc)
        when = (base + timedelta(minutes=minutes)).astimezone(context.zone)
        store.set_time(target, when)
        return Change("snoozed", target, when)


def default_handlers() -> dict[Intent, ActionHandler]:
    return {
        Intent.create: CreateHandler(),
        Intent.reschedule: RescheduleHandler(),
        Intent.snooze: SnoozeHandler(),
        Intent.clarify: NoopHandler(),
        Intent.refuse: NoopHandler(),
    }


class Applier:
    def __init__(self, handlers: Mapping[Intent, ActionHandler] | None = None) -> None:
        self._handlers = dict(handlers) if handlers is not None else default_handlers()

    def apply(
        self, action: ProposedAction, store: ReminderStore, context: CallerContext
    ) -> AppliedResult:
        handler = self._handlers.get(action.intent)
        if handler is None:
            raise UnregisteredIntentError(f"no handler for intent {action.intent.value}")
        change = handler.handle(action, store, context)
        return AppliedResult(
            operation=change.operation,
            affected_id=change.affected_id,
            new_time=change.new_time.isoformat() if change.new_time else None,
            reminders=[
                ReminderOut(id=r.id, title=r.title, time=r.time.isoformat()) for r in store.list()
            ],
        )
