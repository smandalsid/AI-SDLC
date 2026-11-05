"""The one central exception handler: every failure returns the uniform error body."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models.errors import DomainError

HTTP_CODES = {404: ("not_found", "Not found."), 405: ("method_not_allowed", "Method not allowed.")}


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


async def _domain(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)  # noqa: S101  # registered for this type only
    return error_response(exc.http_status, exc.code, exc.message)


async def _validation(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101  # registered for this type only
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", ()) if p != "body")
    message = f"{where}: {first.get('msg', 'invalid request')}" if where else "Invalid request."
    return error_response(422, "invalid_request", message)


async def _http(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101  # registered for this type only
    code, message = HTTP_CODES.get(exc.status_code, ("invalid_request", "Invalid request."))
    return error_response(exc.status_code, code, message)


async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    return error_response(500, "internal_error", "Internal server error.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain)
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(Exception, _unexpected)
