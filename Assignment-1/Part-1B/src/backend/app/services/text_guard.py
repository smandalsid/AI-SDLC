"""FR-8: an over-long text is refused before the prompt is built or the model is called."""

from __future__ import annotations

from app.models.action import Intent, ProposedAction, RefusalReason

MAX_TEXT_CHARS = 1000


def refusal_for(text: str) -> ProposedAction | None:
    """The `too_long` refusal for a text over the limit, else None; length is in characters."""
    if len(text) <= MAX_TEXT_CHARS:
        return None
    return ProposedAction(
        intent=Intent.refuse,
        title=None,
        datetime_iso=None,
        snooze_minutes=None,
        target_reminder_id=None,
        clarification_question=None,
        refusal_reason=RefusalReason.too_long,
        confidence=1.0,
    )
