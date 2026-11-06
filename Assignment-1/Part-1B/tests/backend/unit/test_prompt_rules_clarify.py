"""Clarification rules stated in the system prompt (FR-2, FR-3, FR-4). One key phrase per line."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.covers("FR-2", "FR-3", "FR-4", "AC-4", "AC-5", "AC-6", "AC-7", "AC-34")

PROMPT = Path(__file__).resolve().parents[3] / "prompts" / "system.md"

KEY_PHRASES = {
    "missing task": "clarify when the task is missing",
    "missing time": "clarify when the time is missing",
    "bare tomorrow": 'clarify for a bare "tomorrow" with no time of day',
    "explicit past": 'clarify for an explicit past time such as "yesterday at 3pm"',
    "passed today": "a clock time with no date that has already passed today is a clarification",
    "not next occurrence": "never the next occurrence",
    "dst gap or repeat": "a local time in a daylight-saving gap or repeat is a clarification",
    "pick valid time": "ask the user to pick a valid time",
    "snooze range": "a snooze duration outside 1 to 1440 minutes is a clarification",
    "never clamped": "never clamped",
    "one question": "one question of at most 200 characters",
    "name the field": "name the specific missing field",
    "no invention": "never invent a value for the missing field",
}


@pytest.mark.parametrize("phrase", KEY_PHRASES.values(), ids=KEY_PHRASES.keys())
def test_the_prompt_states_each_clarification_rule_on_one_line(phrase: str) -> None:
    lines = [line.lower() for line in PROMPT.read_text(encoding="utf-8").splitlines()]
    assert any(phrase.lower() in line for line in lines)
