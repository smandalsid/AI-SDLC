"""Orchestrates one request: context, prompt, model, validation, apply (GR-5)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from pydantic import ValidationError

from app.llm.protocol import LLMClient
from app.models.action import ProposedAction, ProposedActionWire
from app.models.errors import LLMOutputError
from app.models.requests import CallerContext, InterpretRequest
from app.models.responses import InterpretResponse
from app.services.applier import ActionApplier
from app.services.clock import Clock
from app.services.prompt_builder import build_prompt
from app.services.store import InMemoryReminderStore, Reminder
from app.services.validator import Rule, run_rules


def _to_domain(wire: ProposedActionWire) -> ProposedAction:
    try:
        return ProposedAction.from_wire(wire)
    except ValidationError as error:
        raise LLMOutputError("schema", str(error)) from error


class Interpreter:
    def __init__(
        self,
        llm: LLMClient,
        clock: Clock,
        applier: ActionApplier,
        rules: Sequence[Rule],
        template: str,
    ) -> None:
        self._llm, self._clock, self._applier = llm, clock, applier
        self._rules, self._template = list(rules), template

    async def interpret(
        self, request: InterpretRequest, correlation_id: str | None = None
    ) -> InterpretResponse:
        context = CallerContext.build(request, self._clock.now())
        prompt = build_prompt(context, request.text, correlation_id or uuid4().hex, self._template)
        result = await self._llm.parse(prompt)
        action = _to_domain(result.wire)
        run_rules(action, context, self._rules)
        store = InMemoryReminderStore(Reminder(r.id, r.title, r.time) for r in context.reminders)
        return InterpretResponse(action=action, applied=self._applier.apply(action, store, context))
