"""Orchestrates one request: context, prompt, model, validation, apply (GR-5)."""

from __future__ import annotations

import logging
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
from app.services.store import Reminder, StoreFactory
from app.services.text_guard import refusal_for
from app.services.validator import Rule, run_rules

logger = logging.getLogger(__name__)


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
        store_factory: StoreFactory,
    ) -> None:
        self._llm, self._clock, self._applier = llm, clock, applier
        self._rules, self._template = list(rules), template
        self._store_factory = store_factory

    async def interpret(
        self, request: InterpretRequest, correlation_id: str | None = None
    ) -> InterpretResponse:
        context = CallerContext.build(request, self._clock.now())
        store = self._store_factory(Reminder(r.id, r.title, r.time) for r in context.reminders)
        action = refusal_for(request.text)
        if action is None:
            prompt = build_prompt(
                context, request.text, correlation_id or uuid4().hex, self._template
            )
            action = _to_domain((await self._llm.parse(prompt)).wire)
            run_rules(action, context, self._rules)
        applied = self._applier.apply(action, store, context)
        logger.info(
            "request handled intent=%s operation=%s", action.intent.value, applied.operation
        )
        return InterpretResponse(action=action, applied=applied)
