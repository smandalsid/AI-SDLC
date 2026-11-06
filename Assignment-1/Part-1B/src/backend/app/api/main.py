"""Application factory: Settings are built at startup so a bad configuration fails fast."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.body_limit import BodyLimitMiddleware
from app.api.errors import register_error_handlers
from app.api.routes import router
from app.llm.copilot_client import CopilotLLMClient
from app.llm.protocol import LLMClient
from app.services.applier import Applier
from app.services.clock import Clock, SystemClock
from app.services.interpreter import Interpreter
from app.services.leak_guard import sentinels_from
from app.services.prompt_builder import load_template
from app.services.store import InMemoryReminderStore
from app.services.validator import default_rules
from app.settings import Settings


def _build_interpreter(settings: Settings, llm: LLMClient, clock: Clock | None) -> Interpreter:
    template = load_template()
    rules = default_rules(sentinels_from(template, settings.secret_values()))
    clock = SystemClock() if clock is None else clock
    return Interpreter(llm, clock, Applier(), rules, template, InMemoryReminderStore)


def create_app(
    settings: Settings | None = None,
    llm_client: LLMClient | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    settings = Settings() if settings is None else settings
    logging.getLogger("app").setLevel(settings.log_level.upper())
    owned: CopilotLLMClient | None = None
    if llm_client is None:
        owned = CopilotLLMClient(settings)
        llm: LLMClient = owned
    else:
        llm = llm_client

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if owned is not None:
            await owned.stop()

    app = FastAPI(title="Natural-Language Reminder Agent", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.interpreter = _build_interpreter(settings, llm, clock)
    register_error_handlers(app)
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.request_body_max_bytes)
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    app.include_router(router)
    return app
