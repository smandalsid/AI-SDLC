"""Target-resolution rules stated in the system prompt (FR-5). One key phrase per line."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.covers("FR-5", "INV-5", "AC-17", "AC-18", "AC-19")

PROMPT = Path(__file__).resolve().parents[3] / "prompts" / "system.md"

KEY_PHRASES = {
    "exactly one match": "resolvable only when exactly one supplied reminder matches",
    "zero or many": "zero matches or multiple matches give `clarify`",
    "pronoun": '"that" or "it" resolves only when exactly one reminder is supplied',
    "empty list": "an empty reminder list gives `clarify`",
    "ids from list": "ids come only from the supplied reminders",
    "null target": "leave `target_reminder_id` null in that clarification",
}


@pytest.mark.parametrize("phrase", KEY_PHRASES.values(), ids=KEY_PHRASES.keys())
def test_the_prompt_states_each_target_rule_on_one_line(phrase: str) -> None:
    lines = [line.lower() for line in PROMPT.read_text(encoding="utf-8").splitlines()]
    assert any(phrase.lower() in line for line in lines)
