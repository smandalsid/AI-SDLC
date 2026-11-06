from collections.abc import Iterable, Iterator
from typing import Protocol, cast

from starlette.routing import Match
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.error_handlers import response_for
from app.core.errors import UnauthenticatedError
from app.core.tokens import InvalidTokenError, TokenCodec, bearer_token

API_PREFIX = "/api/v1/"

PublicOperations = frozenset[tuple[str, str]]


class _Route(Protocol):
    path: str
    methods: set[str] | None

    def matches(self, scope: Scope) -> tuple[Match, Scope]: ...


class _HasRoutes(Protocol):
    @property
    def routes(self) -> Iterable[object]: ...


def _flat_routes(container: _HasRoutes) -> Iterator[_Route]:
    """Routes added with include_router are nested; flatten them to one entry per operation."""
    for route in container.routes:
        nested = getattr(route, "effective_route_contexts", None)
        if callable(nested):
            yield from cast(Iterator[_Route], nested())
        else:
            yield cast(_Route, route)


def public_operations(router: _HasRoutes) -> PublicOperations:
    """The (method, path) pairs of a router: the single source of truth for public routes."""
    return frozenset(
        (method, route.path) for route in _flat_routes(router) for method in route.methods or ()
    )


class AuthGateMiddleware:
    """Default deny: an API route needs a signed token, checked before any body is read."""

    def __init__(self, app: ASGIApp, public_routes: PublicOperations, codec: TokenCodec) -> None:
        self.app = app
        self.public_routes = public_routes
        self.codec = codec

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self._needs_credential(scope):
            await self.app(scope, receive, send)
        elif self._has_valid_token(scope):
            await self.app(scope, receive, send)
        else:
            await response_for(UnauthenticatedError())(scope, receive, send)

    def _needs_credential(self, scope: Scope) -> bool:
        if not scope["path"].startswith(API_PREFIX):
            return False
        partial = False
        for route in _flat_routes(scope["app"].router):
            match, _ = route.matches(scope)
            if match == Match.FULL:
                return (scope["method"], route.path) not in self.public_routes
            partial = partial or match == Match.PARTIAL
        # A real path with another method is protected; a path that matches nothing gets the 404.
        return partial

    def _has_valid_token(self, scope: Scope) -> bool:
        header = next(
            (
                value.decode("latin-1")
                for name, value in scope["headers"]
                if name == b"authorization"
            ),
            None,
        )
        token = bearer_token(header)
        if token is None:
            return False
        try:
            self.codec.decode(token)
        except InvalidTokenError:
            return False
        return True
