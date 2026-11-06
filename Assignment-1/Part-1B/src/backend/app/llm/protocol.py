"""The LLMClient abstraction: services depend on this, never on the SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.action import ProposedActionWire


@dataclass(frozen=True)
class LLMRequest:
    system_prompt: str
    user_message: str
    correlation_id: str


@dataclass(frozen=True)
class CallRecord:
    """Facts about one model call. Never holds prompt text or secrets."""

    model_requested: str
    model_served: str | None
    reasoning_effort: str
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: int
    attempt: int


@dataclass(frozen=True)
class LLMResult:
    wire: ProposedActionWire
    record: CallRecord


@dataclass(frozen=True)
class PreflightResult:
    runtime_ok: bool
    authenticated: bool
    model_in_catalog: bool
    runtime_version: str
    sdk_version: str


class LLMClient(Protocol):
    async def parse(self, request: LLMRequest) -> LLMResult: ...


class Preflight(Protocol):
    async def preflight(self) -> PreflightResult: ...
