"""Replays redacted recorded model outputs: <correlation_id>.json in a directory."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from app.llm.protocol import CallRecord, LLMRequest, LLMResult
from app.models.action import ProposedActionWire
from app.models.errors import LLMInfrastructureError, LLMOutputError


class ReplayLLMClient:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    async def parse(self, request: LLMRequest) -> LLMResult:
        path = self._directory / f"{request.correlation_id}.json"
        if not path.is_file():
            raise LLMInfrastructureError("replay_missing", f"no recording {path.name}")
        try:
            wire = ProposedActionWire.model_validate_json(path.read_text())
        except ValidationError as error:
            raise LLMOutputError("schema", str(error)) from error
        return LLMResult(wire, CallRecord("replay", "replay", "low", None, None, 0, 1))
