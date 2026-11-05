"""Create rules stated in the system prompt (FR-1, FR-3). Key phrases sit on one line each."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.covers("FR-1", "FR-3")

PROMPT = Path(__file__).resolve().parents[3] / "prompts" / "system.md"

KEY_PHRASES = {
    "morning window": "morning 09:00",
    "afternoon window": "afternoon 14:00",
    "evening window": "evening 18:00",
    "night window": "night 21:00",
    "end of day window": "end of day 17:00",
    "bare tomorrow": 'a bare "tomorrow" is a clarification',
    "weekday first occurrence": "first occurrence after the current local date",
    "weekday today": "same weekday one week later",
    "relative minutes": "in 30 minutes",
    "relative days": "in 3 days at 9am",
    "local offset": "caller's local offset",
    "title verbatim": "title is kept verbatim",
    "title summary": "summarised to 120 characters or fewer without changing meaning",
    "no invention": "never invent the task or the time",
}


@pytest.mark.parametrize("phrase", KEY_PHRASES.values(), ids=KEY_PHRASES.keys())
def test_the_prompt_states_each_create_rule_on_one_line(phrase: str) -> None:
    lines = [line.lower() for line in PROMPT.read_text(encoding="utf-8").splitlines()]
    assert any(phrase.lower() in line for line in lines)
