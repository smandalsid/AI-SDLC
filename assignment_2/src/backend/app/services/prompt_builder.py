"""Builds the model prompt: fixed rules, a deterministic context block, JSON-encoded data."""

from __future__ import annotations

import json
from pathlib import Path

from app.llm.protocol import LLMRequest
from app.models.requests import CallerContext
from app.services.calendar_context import reference_calendar

CANARY_PHRASE = "CANARY-REMINDER-AGENT-7f3a91"
DATA_START = "<<<REQUEST_DATA"
DATA_END = "REQUEST_DATA>>>"
PROMPT_PATH = Path(__file__).resolve().parents[4] / "prompts" / "system.md"


def load_template(path: Path = PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


def _encode(payload: object) -> str:
    # Escaping angle brackets means user text can never reproduce a block delimiter.
    return json.dumps(payload).replace("<", "\\u003c").replace(">", "\\u003e")


def build_prompt(
    context: CallerContext, text: str, correlation_id: str, template: str
) -> LLMRequest:
    calendar = reference_calendar(context.zone, context.now_utc)
    system = f"{template.rstrip()}\n\n## Context for this request\n{calendar}\n"
    reminders = [
        {"id": r.id, "title": r.title, "time": r.time.isoformat()} for r in context.reminders
    ]
    user = f"{DATA_START}\n{_encode({'text': text, 'reminders': reminders})}\n{DATA_END}"
    return LLMRequest(system, user, correlation_id)
