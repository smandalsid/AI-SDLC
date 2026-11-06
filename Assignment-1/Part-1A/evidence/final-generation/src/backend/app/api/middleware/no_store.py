from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

API_PREFIX = "/api/v1"


class NoStoreMiddleware:
    """Stops browsers and proxies caching API answers, so signed-out data is never replayed."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self._is_api(scope["path"]):
            await self.app(scope, receive, send)
            return

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, send_with_header)

    @staticmethod
    def _is_api(path: str) -> bool:
        return path == API_PREFIX or path.startswith(f"{API_PREFIX}/")
