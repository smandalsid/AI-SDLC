"""A scripted LLMClient for tests and the evaluation executor."""

from __future__ import annotations

from app.llm.protocol import CallRecord, LLMRequest, LLMResult
from app.models.action import ProposedActionWire

Scripted = dict[str, object] | ProposedActionWire | BaseException


class StubLLMClient:
    """Returns the scripted responses in order and repeats the last one when exhausted."""

    def __init__(self, *responses: Scripted) -> None:
        self._responses = list(responses)
        self.calls = 0
        self.requests: list[LLMRequest] = []

    async def parse(self, request: LLMRequest) -> LLMResult:
        self.calls += 1
        self.requests.append(request)
        item = self._responses[min(self.calls, len(self._responses)) - 1]
        if isinstance(item, BaseException):
            raise item
        wire = (
            item
            if isinstance(item, ProposedActionWire)
            else ProposedActionWire.model_validate(item)
        )
        return LLMResult(wire, CallRecord("stub", "stub", "low", 0, 0, 0, 1))
