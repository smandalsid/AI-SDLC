"""Regressions from the live run 20261105T182821Z (cases N05, B05, M04). One key phrase per line."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.covers("FR-3", "FR-4", "FR-8", "AC-7", "AC-16", "AC-37")

PROMPT = Path(__file__).resolve().parents[3] / "prompts" / "system.md"

KEY_PHRASES = {
    "N05 time still ahead is valid": "a time that is still ahead of the local now today is valid",
    "N05 end of day today": (
        "end of day today is 17:00 today and is valid while the local now is before 17:00"
    ),
    "B05 repeated request": "a text that repeats the same request several times is one reminder",
    "B05 bulk meaning": ("`bulk_action` means one request that changes many existing reminders"),
    "M04 past time question": "says it is in the past and asks for a new date and time",
}


@pytest.mark.parametrize("phrase", KEY_PHRASES.values(), ids=KEY_PHRASES.keys())
def test_the_prompt_states_each_rule_that_a_live_run_showed_was_missing(phrase: str) -> None:
    lines = [line.lower() for line in PROMPT.read_text(encoding="utf-8").splitlines()]
    assert any(phrase.lower() in line for line in lines)
