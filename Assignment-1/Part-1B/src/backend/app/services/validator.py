"""Validation rules applied to the model's action before anything is applied (GR-5)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from app.models.action import Intent, ProposedAction
from app.models.errors import LLMOutputError
from app.models.requests import CallerContext
from app.services.calendar_context import local_time_status

Rule = Callable[[ProposedAction, CallerContext], None]


def target_in_supplied_list(action: ProposedAction, context: CallerContext) -> None:
    """INV-5: a target id must come from the supplied reminders, never from the model."""
    supplied = {r.id for r in context.reminders}
    if action.target_reminder_id is not None and action.target_reminder_id not in supplied:
        raise LLMOutputError("unknown_target", f"unknown id {action.target_reminder_id!r}")


def _proposed_time(action: ProposedAction) -> datetime | None:
    if action.intent in (Intent.create, Intent.reschedule) and action.datetime_iso:
        return datetime.fromisoformat(action.datetime_iso)
    return None


def time_is_future(action: ProposedAction, context: CallerContext) -> None:
    """FR-1: the proposed time must be strictly after now."""
    when = _proposed_time(action)
    if when is not None and when <= context.now_utc:
        raise LLMOutputError("not_future", f"{action.datetime_iso} is not after now")


def wall_time_is_unambiguous(action: ProposedAction, context: CallerContext) -> None:
    """FR-1: the local wall-clock time must exist exactly once in the zone."""
    when = _proposed_time(action)
    if when is not None and local_time_status(context.zone, when.replace(tzinfo=None)) != "exists":
        raise LLMOutputError(
            "nonexistent_or_ambiguous_time", f"{action.datetime_iso} is not a unique local time"
        )


def offset_matches_zone(action: ProposedAction, context: CallerContext) -> None:
    """FR-1: the offset must be the zone's offset at that instant."""
    when = _proposed_time(action)
    if when is not None and when.astimezone(context.zone).utcoffset() != when.utcoffset():
        raise LLMOutputError("offset_mismatch", f"{action.datetime_iso} has the wrong offset")


def default_rules() -> list[Rule]:
    return [
        target_in_supplied_list,
        time_is_future,
        wall_time_is_unambiguous,
        offset_matches_zone,
    ]


def run_rules(action: ProposedAction, context: CallerContext, rules: Sequence[Rule]) -> None:
    for rule in rules:
        rule(action, context)
