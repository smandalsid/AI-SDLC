"""FastAPI dependency wiring: services come from the app state, never built inline."""

from __future__ import annotations

from fastapi import Request

from app.services.interpreter import Interpreter


def get_interpreter(request: Request) -> Interpreter:
    interpreter: Interpreter = request.app.state.interpreter
    return interpreter
