"""Validation rules applied to the model's action before anything is applied (GR-5)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from app.models.action import ProposedAction
from app.models.errors import LLMOutputError
from app.models.requests import CallerContext

Rule = Callable[[ProposedAction, CallerContext], None]


def target_in_supplied_list(action: ProposedAction, context: CallerContext) -> None:
    """INV-5: a target id must come from the supplied reminders, never from the model."""
    supplied = {r.id for r in context.reminders}
    if action.target_reminder_id is not None and action.target_reminder_id not in supplied:
        raise LLMOutputError("unknown_target", f"unknown id {action.target_reminder_id!r}")


def default_rules() -> list[Rule]:
    return [target_in_supplied_list]


def run_rules(action: ProposedAction, context: CallerContext, rules: Sequence[Rule]) -> None:
    for rule in rules:
        rule(action, context)
