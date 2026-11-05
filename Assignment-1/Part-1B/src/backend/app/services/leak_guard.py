"""GR-4 backstop: no output field may contain the prompt canary or a configured secret."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from app.models.action import ProposedAction

CANARY_PATTERN = re.compile(r"CANARY-[A-Za-z0-9-]+")


def sentinels_from(template: str, secrets: Iterable[str]) -> list[str]:
    """Canary phrases found in the system prompt, then the non-blank secret values."""
    return [*CANARY_PATTERN.findall(template), *(s for s in secrets if s.strip())]


def leaked_field(action: ProposedAction, sentinels: Sequence[str]) -> str | None:
    """Name of the first output field that contains a sentinel (case-insensitive), else None."""
    wanted = [s.casefold() for s in sentinels if s]
    for name, value in action.model_dump(mode="json").items():
        if isinstance(value, str) and any(s in value.casefold() for s in wanted):
            return name
    return None
