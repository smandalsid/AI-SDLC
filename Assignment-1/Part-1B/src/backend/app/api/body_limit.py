"""Transport-level request body limit: a larger body is a 413 before any parsing."""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.errors import error_response
from app.models.errors import PayloadTooLarge


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self._app, self._max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        declared = Headers(scope=scope).get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            await self._reject(scope, receive, send)
            return
        buffered = await self._read_within_limit(receive)
        if buffered is None:
            await self._reject(scope, receive, send)
            return
        await self._app(scope, _replay(buffered, receive), send)

    async def _read_within_limit(self, receive: Receive) -> list[Message] | None:
        """The whole body as messages, or None as soon as it exceeds the limit."""
        messages: list[Message] = []
        total = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                return messages
            total += len(message.get("body", b""))
            if total > self._max_bytes:
                return None
            if not message.get("more_body", False):
                return messages

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        error = PayloadTooLarge("The request body is too large.")
        await error_response(error.http_status, error.code, error.message)(scope, receive, send)


def _replay(messages: list[Message], receive: Receive) -> Receive:
    pending = iter(messages)

    async def replay() -> Message:
        return next(pending, None) or await receive()

    return replay
