"""Stub and replay clients behind the LLMClient Protocol; CallRecord content (GR-4)."""

import dataclasses
import json
from pathlib import Path

import pytest
from app_helpers import action_dict, create_dict

from app.llm.protocol import CallRecord, LLMRequest
from app.llm.replay_client import ReplayLLMClient
from app.llm.stub_client import StubLLMClient
from app.models.errors import LLMInfrastructureError, LLMOutputError

pytestmark = pytest.mark.covers("GR-4", "FR-14", "AC-29")


def _request(correlation_id: str = "N01.1") -> LLMRequest:
    return LLMRequest("SYSTEM PROMPT", "USER DATA", correlation_id)


async def test_stub_returns_scripted_actions_in_order_and_counts_calls() -> None:
    stub = StubLLMClient(create_dict(), action_dict())
    first = await stub.parse(_request())
    second = await stub.parse(_request())
    assert first.wire.intent == "create" and second.wire.intent == "clarify"
    assert stub.calls == 2 and stub.requests[0].user_message == "USER DATA"


async def test_stub_repeats_its_last_response() -> None:
    stub = StubLLMClient(create_dict())
    await stub.parse(_request())
    assert (await stub.parse(_request())).wire.intent == "create"


async def test_stub_raises_scripted_faults() -> None:
    stub = StubLLMClient(LLMInfrastructureError("timeout", "slow"))
    with pytest.raises(LLMInfrastructureError):
        await stub.parse(_request())
    assert stub.calls == 1


async def test_replay_reads_the_recorded_action_for_the_correlation_id(tmp_path: Path) -> None:
    (tmp_path / "N01.1.json").write_text(json.dumps(create_dict()))
    result = await ReplayLLMClient(tmp_path).parse(_request("N01.1"))
    assert result.wire.title == "pay rent"


async def test_replay_with_a_missing_fixture_is_a_controlled_infrastructure_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(LLMInfrastructureError) as info:
        await ReplayLLMClient(tmp_path).parse(_request("N99.1"))
    assert info.value.kind == "replay_missing"


async def test_replay_with_an_invalid_fixture_is_an_output_error(tmp_path: Path) -> None:
    (tmp_path / "N01.1.json").write_text('{"intent": "create"}')
    with pytest.raises(LLMOutputError):
        await ReplayLLMClient(tmp_path).parse(_request("N01.1"))


def test_call_record_has_the_documented_fields_and_no_prompt_text() -> None:
    names = {f.name for f in dataclasses.fields(CallRecord)}
    assert names == {
        "model_requested",
        "model_served",
        "reasoning_effort",
        "input_tokens",
        "output_tokens",
        "duration_ms",
        "attempt",
    }
    record = CallRecord("m", "m", "low", 1, 2, 3, 1)
    assert "SYSTEM PROMPT" not in repr(record)
