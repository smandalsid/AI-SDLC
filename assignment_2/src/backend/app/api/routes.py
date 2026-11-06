"""HTTP routes: request and response handling only, no business logic."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_interpreter
from app.models.requests import InterpretRequest
from app.models.responses import ErrorBody, InterpretResponse
from app.services.interpreter import Interpreter

router = APIRouter(prefix="/api/v1")
ERROR_STATUSES = (413, 422, 500, 502, 503, 504)


@router.post(
    "/actions",
    response_model=InterpretResponse,
    responses={status: {"model": ErrorBody} for status in ERROR_STATUSES},
)
async def interpret(
    request: InterpretRequest, interpreter: Annotated[Interpreter, Depends(get_interpreter)]
) -> InterpretResponse:
    return await interpreter.interpret(request)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
