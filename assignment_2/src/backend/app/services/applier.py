"""Applies a validated action to the in-memory store through a registry of handlers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

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


def default_handlers() -> dict[Intent, ActionHandler]:
    return {Intent.clarify: NoopHandler(), Intent.refuse: NoopHandler()}


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
