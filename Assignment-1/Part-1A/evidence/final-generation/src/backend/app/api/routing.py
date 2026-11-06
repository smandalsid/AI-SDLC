import json
from collections.abc import Callable, Coroutine

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.types import Message, Receive


def _single_message(body: bytes) -> Receive:
    delivered = False

    async def receive() -> Message:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _unparsable_json(content_type: str, body: bytes) -> bool:
    if not body or ("json" not in content_type and content_type != ""):
        return False
    try:
        json.loads(body)
    except ValueError:
        return True
    return False


class SessionFirstRoute(APIRoute):
    """FastAPI reports an unparsable JSON body before it runs the dependencies, which would let
    a caller without a valid session see a 422. The body is handed over as `null` instead, so the
    session check refuses first and a valid session still gets the validation error."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[object, object, Response]]:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            body = await request.body()
            if _unparsable_json(request.headers.get("content-type", ""), body):
                request = Request(request.scope, _single_message(b"null"))
            return await original(request)

        return handler
