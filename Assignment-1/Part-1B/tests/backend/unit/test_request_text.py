"""Request text: empty, whitespace-only and non-text are rejected; no cap here (FR-8)."""

import pytest
from pydantic import ValidationError

from app.models.requests import InterpretRequest

pytestmark = pytest.mark.covers("FR-8", "AC-15", "AC-14")


@pytest.mark.parametrize("text", ["", " ", "   ", "\t", "\n", " \t\r\n ", "\u00a0", "\u2003"])
def test_empty_and_whitespace_only_text_is_rejected(text: str) -> None:
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": text})


@pytest.mark.parametrize("text", [12345, 1.5, True, None, ["remind me"], {"a": 1}])
def test_non_text_is_rejected(text: object) -> None:
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": text})


@pytest.mark.parametrize("text", ["x", " remind me ", "x" * 1000, "x" * 1001, "x" * 50_000])
def test_any_non_blank_text_is_accepted_at_the_schema_level(text: str) -> None:
    assert InterpretRequest.model_validate({"text": text}).text == text
