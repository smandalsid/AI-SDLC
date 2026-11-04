import base64
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

import pytest
from app.core.tokens import JwtTokenCodec, TokenClaims, get_token_codec
from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

API = "/api/v1"
PROTECTED = [
    pytest.param("GET", "/buses", id="list-buses"),
    pytest.param("GET", "/buses/1", id="bus-detail"),
    pytest.param("POST", "/bookings", id="create-booking"),
    pytest.param("GET", "/auth/me", id="me"),
]
UNAUTHENTICATED = {"error": {"code": "unauthenticated", "message": "Authentication required."}}
COUNTS = text(
    "SELECT (SELECT COUNT(*) FROM bookings), (SELECT COUNT(*) FROM sessions), "
    "(SELECT COUNT(*) FROM sign_in_attempts)"
)
BOOKING = {"bus_id": 1, "seat_numbers": [3]}


@dataclass
class Attempt:
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    body: object | None = None
    raw_body: bytes | None = None


@dataclass(frozen=True)
class Context:
    token: str
    session_id: str
    factory: sessionmaker[Session]


Technique = Callable[[Context], Attempt]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def altered(ctx: Context) -> Attempt:
    middle = len(ctx.token) - 10
    changed = "A" if ctx.token[middle] != "A" else "B"
    return Attempt(headers=bearer(ctx.token[:middle] + changed + ctx.token[middle + 1 :]))


def signed_with_another_key(ctx: Context) -> Attempt:
    other = JwtTokenCodec(SecretStr("another-signing-key-" + "z" * 24))
    claims = get_token_codec().decode(ctx.token)
    return Attempt(headers=bearer(other.encode(claims, datetime.now(UTC))))


def alg_none(ctx: Context) -> Attempt:
    def part(value: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()

    claims = get_token_codec().decode(ctx.token)
    payload = {
        "sid": claims.session_id,
        "sub": "1",
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int(claims.expires_at.timestamp()),
    }
    return Attempt(headers=bearer(f"{part({'alg': 'none', 'typ': 'JWT'})}.{part(payload)}."))


def session_row_deleted(ctx: Context) -> Attempt:
    with ctx.factory() as session:
        session.execute(text("DELETE FROM sessions"))
        session.commit()
    return Attempt(headers=bearer(ctx.token))


def another_users_subject(ctx: Context) -> Attempt:
    forged = TokenClaims(ctx.session_id, 2, datetime.now(UTC) + timedelta(minutes=30))
    return Attempt(headers=bearer(get_token_codec().encode(forged, datetime.now(UTC))))


# Each technique with the status it must produce; later stories append `signed-out` and `expired`.
TECHNIQUES = [
    pytest.param(lambda ctx: Attempt(), 401, id="no-header"),
    pytest.param(lambda ctx: Attempt(headers={"Authorization": ""}), 401, id="empty-header"),
    pytest.param(lambda ctx: Attempt(headers={"Authorization": "Bearer"}), 401, id="bearer-only"),
    pytest.param(
        lambda ctx: Attempt(headers={"Authorization": "Basic YXNoYTpwYXNz"}), 401, id="basic-scheme"
    ),
    pytest.param(lambda ctx: Attempt(headers=bearer(token_urlsafe(40))), 401, id="random-token"),
    pytest.param(altered, 401, id="one-character-changed"),
    pytest.param(signed_with_another_key, 401, id="other-signing-key"),
    pytest.param(alg_none, 401, id="alg-none"),
    pytest.param(session_row_deleted, 401, id="session-row-deleted"),
    pytest.param(another_users_subject, 401, id="other-users-subject"),
    pytest.param(lambda ctx: Attempt(body=BOOKING), 401, id="valid-body-without-session"),
    pytest.param(
        lambda ctx: Attempt(raw_body=b"{not json", headers={"Content-Type": "application/json"}),
        401,
        id="malformed-json-without-session",
    ),
    pytest.param(lambda ctx: Attempt(headers={"X-User-Id": "1"}), 401, id="identity-header"),
    pytest.param(lambda ctx: Attempt(params={"user_id": "1"}), 401, id="identity-query"),
    pytest.param(
        lambda ctx: Attempt(headers={"Cookie": "session=1; signed_in=true"}), 401, id="cookies"
    ),
    pytest.param(lambda ctx: Attempt(body={**BOOKING, "user_id": 1}), 401, id="identity-in-body"),
    pytest.param(lambda ctx: Attempt(params={"access_token": ctx.token}), 401, id="token-in-query"),
]


def counts(factory: sessionmaker[Session]) -> tuple[int, int, int]:
    with factory() as session:
        first, second, third = session.execute(COUNTS).one()
    return int(first), int(second), int(third)


def send(client: TestClient, method: str, path: str, attempt: Attempt) -> Response:
    return client.request(
        method,
        f"{API}{path}",
        headers=attempt.headers,
        params=attempt.params,
        json=attempt.body,
        content=attempt.raw_body,
    )


@pytest.fixture
def context(sign_in: Callable[[str], Response], session_factory: sessionmaker[Session]) -> Context:
    token = sign_in("asha").json()["access_token"]
    return Context(token, get_token_codec().decode(token).session_id, session_factory)


@pytest.mark.parametrize(("method", "path"), PROTECTED)
@pytest.mark.parametrize(("technique", "expected_status"), TECHNIQUES)
def test_every_technique_is_refused_on_every_protected_route_and_stores_nothing(
    client: TestClient,
    session_factory: sessionmaker[Session],
    context: Context,
    technique: Technique,
    expected_status: int,
    method: str,
    path: str,
) -> None:
    attempt = technique(context)
    before = counts(session_factory)

    response = send(client, method, path, attempt)

    assert response.status_code == expected_status
    assert response.json() == UNAUTHENTICATED
    assert response.headers["www-authenticate"] == "Bearer"
    assert counts(session_factory) == before


@pytest.mark.parametrize(("method", "path"), [("DELETE", "/buses"), ("PUT", "/bookings")])
def test_a_wrong_method_on_a_protected_address_is_refused_as_unauthenticated(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method, f"{API}{path}")

    assert response.status_code == 401
    assert response.json() == UNAUTHENTICATED


@pytest.mark.parametrize("path", ["/buses/1/extra", "/auth/unknown"])
def test_an_address_that_matches_no_route_is_a_plain_404_without_data(
    client: TestClient, path: str
) -> None:
    response = client.get(f"{API}{path}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "www-authenticate" not in response.headers
    assert "Bus A" not in response.text


def test_a_trailing_slash_reveals_no_data_without_a_credential(client: TestClient) -> None:
    response = client.get(f"{API}/buses/", follow_redirects=False)

    assert response.status_code in (307, 401, 404)
    followed = client.get(f"{API}/buses/")
    assert followed.status_code in (401, 404)
    assert "Bus A" not in followed.text
