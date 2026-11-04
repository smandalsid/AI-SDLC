from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.api.error_handlers import register_error_handlers
from app.api.middleware.auth_gate import AuthGateMiddleware, public_operations
from app.api.middleware.no_store import NoStoreMiddleware
from app.api.v1.router import api_router, public_router
from app.core.config import get_settings
from app.core.tokens import get_token_codec
from app.db.session import wait_for_database


def create_app(wait_for_db: Callable[[], None] = wait_for_database) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Not ready until the database answers; if it never does, startup fails.
        await run_in_threadpool(wait_for_db)
        yield

    app = FastAPI(
        title="Bus Booking API",
        version="1.0.0",
        lifespan=lifespan,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )
    app.add_middleware(
        AuthGateMiddleware, public_routes=public_operations(public_router), codec=get_token_codec()
    )
    # Outside the gate, so its 401 is marked too; inside CORS.
    app.add_middleware(NoStoreMiddleware)
    # Added last so CORS is outermost: preflight requests are answered before the gate sees them.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type", "authorization"],
    )
    register_error_handlers(app)
    app.include_router(api_router)
    return app
