"""Cancel rules stated in the system prompt (FR-7, GR-2). One key phrase per line."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.covers("FR-7", "GR-2", "AC-9", "AC-22")

PROMPT = Path(__file__).resolve().parents[3] / "prompts" / "system.md"

KEY_PHRASES = {
    "one reminder": "cancel targets exactly one reminder",
    "bulk refusal": '"cancel everything" and similar requests are `refuse` with `bulk_action`',
    "never several": "never several cancels",
}


@pytest.mark.parametrize("phrase", KEY_PHRASES.values(), ids=KEY_PHRASES.keys())
def test_the_prompt_states_each_cancel_rule_on_one_line(phrase: str) -> None:
    lines = [line.lower() for line in PROMPT.read_text(encoding="utf-8").splitlines()]
    assert any(phrase.lower() in line for line in lines)
