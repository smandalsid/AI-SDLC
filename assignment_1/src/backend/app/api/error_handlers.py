import logging
import traceback
from http import HTTPStatus
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, TooManyAttemptsError, UnauthenticatedError

logger = logging.getLogger(__name__)

STATUS_BY_CODE = {
    "invalid_seat": 400,
    "unauthenticated": 401,
    "invalid_credentials": 401,
    "bus_not_found": 404,
    "user_not_found": 404,
    "seat_unavailable": 409,
    "too_many_attempts": 429,
}
CODE_BY_HTTP_STATUS = {404: "not_found", 405: "method_not_allowed"}
MAX_DETAIL_LENGTH = 200


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def response_for(error: AppError) -> JSONResponse:
    """The only place a domain error becomes a response; also used where nothing may be raised."""
    response = error_response(STATUS_BY_CODE.get(error.code, 500), error.code, error.message)
    if isinstance(error, UnauthenticatedError):
        response.headers["WWW-Authenticate"] = "Bearer"
    if isinstance(error, TooManyAttemptsError):
        response.headers["Retry-After"] = str(error.retry_after_seconds)
    return response


async def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    return response_for(cast(AppError, exc))  # registered for AppError only


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    error = cast(RequestValidationError, exc)
    # Only the offending field locations are reported, never the submitted values.
    where = ", ".join(".".join(str(part) for part in item["loc"]) for item in error.errors())
    return error_response(422, "validation_error", f"Invalid request: {where}"[:MAX_DETAIL_LENGTH])


async def handle_http_error(request: Request, exc: Exception) -> JSONResponse:
    error = cast(StarletteHTTPException, exc)
    code = CODE_BY_HTTP_STATUS.get(error.status_code, "http_error")
    return error_response(error.status_code, code, HTTPStatus(error.status_code).phrase)


async def handle_database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    logger.error("database unavailable (%s)", type(exc).__name__)
    return error_response(503, "service_unavailable", "The service is temporarily unavailable.")


async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    # Frames only: exception messages can carry connection details or user data.
    frames = "".join(traceback.format_tb(exc.__traceback__))
    logger.error("unhandled %s\n%s", type(exc).__name__, frames)
    return error_response(500, "internal_error", "An unexpected error occurred.")


def register_error_handlers(app: FastAPI) -> None:
    """The only place exceptions become HTTP responses."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(OperationalError, handle_database_unavailable)
    app.add_exception_handler(PoolTimeoutError, handle_database_unavailable)
    app.add_exception_handler(Exception, handle_unexpected)
