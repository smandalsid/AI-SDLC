from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.api.error_handlers import register_error_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import wait_for_database


def create_app(wait_for_db: Callable[[], None] = wait_for_database) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Not ready until the database answers; if it never does, startup fails.
        await run_in_threadpool(wait_for_db)
        yield

    app = FastAPI(title="Bus Booking API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )
    register_error_handlers(app)
    app.include_router(api_router)
    return app
