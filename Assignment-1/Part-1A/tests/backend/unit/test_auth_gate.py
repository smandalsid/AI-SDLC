import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from app.api.middleware.auth_gate import AuthGateMiddleware, public_operations
from app.core.tokens import JwtTokenCodec, TokenClaims
from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import SecretStr
from starlette.types import Message, Scope

NOW = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
CODEC = JwtTokenCodec(SecretStr("unit-test-signing-" + "k" * 24))
OTHER_CODEC = JwtTokenCodec(SecretStr("another-signing-key-" + "z" * 24))
UNAUTHENTICATED = {"error": {"code": "unauthenticated", "message": "Authentication required."}}


def token_from(codec: JwtTokenCodec) -> str:
    return codec.encode(TokenClaims("s" * 32, 1, NOW + timedelta(minutes=30)), NOW)


def build() -> tuple[FastAPI, APIRouter]:
    public = APIRouter(prefix="/api/v1")
    protected = APIRouter(prefix="/api/v1")

    @public.get("/open")
    def open_route() -> dict[str, str]:
        return {"route": "open"}

    @protected.get("/closed")
    def closed_route() -> dict[str, str]:
        return {"route": "closed"}

    @protected.post("/echo")
    async def echo_route(request: Request) -> dict[str, int]:
        return {"length": len(await request.body())}

    app = FastAPI()
    app.include_router(public)
    app.include_router(protected)
    app.add_api_route("/outside", open_route)
    app.add_middleware(AuthGateMiddleware, public_routes=public_operations(public), codec=CODEC)
    return app, public


@pytest.fixture
def client() -> TestClient:
    app, _ = build()
    return TestClient(app, raise_server_exceptions=False)


def test_a_public_route_passes_without_a_header(client: TestClient) -> None:
    assert client.get("/api/v1/open").status_code == 200


def test_a_path_outside_the_api_prefix_is_not_gated(client: TestClient) -> None:
    assert client.get("/outside").status_code == 200


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        "Bearer",
        "Bearer ",
        "Basic dXNlcjpwYXNz",
        "Bearer not-a-token",
        "Bearer " + token_from(OTHER_CODEC),
    ],
    ids=["none", "empty", "bearer-only", "bearer-space", "basic", "garbage", "other-key"],
)
def test_a_protected_route_refuses_a_missing_or_bad_credential_identically(
    client: TestClient, header: str | None
) -> None:
    headers = {} if header is None else {"Authorization": header}

    response = client.get("/api/v1/closed", headers=headers)

    assert response.status_code == 401
    assert response.json() == UNAUTHENTICATED
    assert response.headers["www-authenticate"] == "Bearer"


def test_a_correctly_signed_token_reaches_the_application(client: TestClient) -> None:
    response = client.get(
        "/api/v1/closed", headers={"Authorization": f"Bearer {token_from(CODEC)}"}
    )

    assert response.status_code == 200


def test_a_known_path_with_the_wrong_method_is_protected(client: TestClient) -> None:
    response = client.delete("/api/v1/closed")

    assert response.status_code == 401
    assert response.json() == UNAUTHENTICATED


def test_a_path_that_matches_no_route_falls_through_to_the_application_404(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/nowhere")

    assert response.status_code == 404
    assert "www-authenticate" not in response.headers


def test_a_route_added_outside_the_public_router_is_protected_by_default() -> None:
    app, _ = build()
    app.add_api_route("/api/v1/added-later", lambda: {"route": "added"})
    client = TestClient(app, raise_server_exceptions=False)

    assert client.get("/api/v1/added-later").status_code == 401


def test_the_public_set_comes_from_the_public_router_object() -> None:
    _, public = build()

    assert public_operations(public) == frozenset({("GET", "/api/v1/open")})


def test_a_rejected_request_never_reads_its_body() -> None:
    app, public = build()
    gate = AuthGateMiddleware(app, public_operations(public), CODEC)
    sent: list[Message] = []

    async def receive() -> Message:
        raise AssertionError("the request body must not be read")

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "path": "/api/v1/echo",
        "raw_path": b"/api/v1/echo",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "app": app,
    }

    asyncio.run(gate(scope, receive, send))

    assert sent[0]["status"] == 401
    assert (b"www-authenticate", b"Bearer") in sent[0]["headers"]
    assert json.loads(sent[1]["body"]) == UNAUTHENTICATED
