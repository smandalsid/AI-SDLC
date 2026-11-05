"""Application factory: Settings are built at startup so a bad configuration fails fast."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.llm.copilot_client import CopilotLLMClient
from app.llm.protocol import LLMClient
from app.services.applier import Applier
from app.services.clock import Clock, SystemClock
from app.services.interpreter import Interpreter
from app.services.prompt_builder import load_template
from app.services.validator import default_rules
from app.settings import Settings


def create_app(
    settings: Settings | None = None,
    llm_client: LLMClient | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    settings = Settings() if settings is None else settings
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
    app.state.interpreter = Interpreter(
        llm, SystemClock() if clock is None else clock, Applier(), default_rules(), load_template()
    )
    register_error_handlers(app)
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    app.include_router(router)
    return app
