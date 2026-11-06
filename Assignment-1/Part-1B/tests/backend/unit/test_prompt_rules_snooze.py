"""Snooze rules stated in the system prompt (FR-6). One key phrase per line."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.covers("FR-6", "INV-4", "AC-20", "AC-21")

PROMPT = Path(__file__).resolve().parents[3] / "prompts" / "system.md"

KEY_PHRASES = {
    "whole minutes": "convert the duration to whole minutes",
    "hours": '"2 hours" is 120 minutes',
    "range": "a duration outside 1 to 1440 minutes gives `clarify` and is never clamped",
    "target and minutes": "return the target and `snooze_minutes`, never a new time",
}


@pytest.mark.parametrize("phrase", KEY_PHRASES.values(), ids=KEY_PHRASES.keys())
def test_the_prompt_states_each_snooze_rule_on_one_line(phrase: str) -> None:
    lines = [line.lower() for line in PROMPT.read_text(encoding="utf-8").splitlines()]
    assert any(phrase.lower() in line for line in lines)
