import logging
from collections.abc import Mapping

from app.core.config import get_settings
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from pytest import LogCaptureFixture
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

MARKER_HOST = "db-secret-host.internal"


def test_500_and_503_responses_and_logs_do_not_leak_secrets(
    app: FastAPI, client: TestClient, caplog: LogCaptureFixture
) -> None:
    settings = get_settings()
    password = settings.db_password.get_secret_value()
    url = settings.database_url(settings.db_name).render_as_string(hide_password=False)

    def unexpected() -> None:
        raise RuntimeError(f"connect failed {url} password={password}")

    def unreachable() -> None:
        raise OperationalError("SELECT 1", {}, Exception(f"cannot reach {MARKER_HOST}"))

    app.add_api_route("/__unexpected", unexpected)
    app.add_api_route("/__unreachable", unreachable)
    caplog.set_level(logging.DEBUG)

    responses = [client.get("/__unexpected"), client.get("/__unreachable")]

    assert [response.status_code for response in responses] == [500, 503]
    everything = "\n".join([response.text for response in responses]) + caplog.text
    for secret in (password, url, MARKER_HOST):
        assert secret not in everything


LOGIN = "/api/v1/auth/login"
WRONG = "wrong-password-value"


def settings_secret() -> str:
    return get_settings().jwt_secret.get_secret_value()


def stored_hashes(factory: sessionmaker[Session]) -> list[str]:
    with factory() as session:
        return [str(row[0]) for row in session.execute(text("SELECT password_hash FROM users"))]


def attempt_rows(factory: sessionmaker[Session]) -> str:
    with factory() as session:
        rows = session.execute(text("SELECT username, outcome, attempted_at FROM sign_in_attempts"))
        return "\n".join(" ".join(str(value) for value in row) for row in rows)


def test_no_password_hash_token_or_signing_key_leaks_through_any_channel(
    app: FastAPI,
    client: TestClient,
    caplog: LogCaptureFixture,
    session_factory: sessionmaker[Session],
    credentials: Mapping[str, str],
) -> None:
    caplog.set_level(logging.DEBUG)
    responses: list[Response] = []

    def failing() -> None:
        raise RuntimeError("unexpected failure")

    def unreachable() -> None:
        raise OperationalError("SELECT 1", {}, Exception("cannot reach the database"))

    app.add_api_route("/api/v1/__unexpected", failing)
    app.add_api_route("/api/v1/__unreachable", unreachable)

    login = client.post(LOGIN, json={"username": "asha", "password": credentials["asha"]})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    responses += [
        client.get("/api/v1/auth/me", headers=headers),
        client.get("/api/v1/buses", headers=headers),
        client.post("/api/v1/bookings", json={"bus_id": 1, "seat_numbers": [3]}, headers=headers),
        client.get("/api/v1/__unexpected", headers=headers),
        client.get("/api/v1/__unreachable", headers=headers),
        client.post(LOGIN, json={"username": "nobody", "password": WRONG}),
        client.post(LOGIN, json={"username": "asha", "password": WRONG}),
        client.post(LOGIN, content=b"{not json", headers={"Content-Type": "application/json"}),
        client.get("/api/v1/buses", headers={"Authorization": "Bearer " + "x" * 40}),
        client.post("/api/v1/auth/logout", headers=headers),
        client.get("/api/v1/auth/me", headers=headers),
    ]
    for _ in range(5):
        client.post(LOGIN, json={"username": "ravi", "password": WRONG})
    responses.append(client.post(LOGIN, json={"username": "ravi", "password": credentials["ravi"]}))

    assert {response.status_code for response in responses} >= {
        200,
        201,
        204,
        401,
        422,
        429,
        500,
        503,
    }
    shared = [WRONG, settings_secret(), *credentials.values(), *stored_hashes(session_factory)]
    for response in [login, *responses]:
        surface = response.text + str(dict(response.headers)) + str(response.request.url)
        assert not [secret for secret in shared if secret in surface]
        assert token not in str(dict(response.headers)) + str(response.request.url)
        if response is not login:
            assert token not in response.text
    stored = attempt_rows(session_factory) + caplog.text
    assert not [secret for secret in [*shared, token] if secret in stored]


def test_no_username_or_password_reaches_a_log_line(
    client: TestClient, caplog: LogCaptureFixture, credentials: Mapping[str, str]
) -> None:
    caplog.set_level(logging.DEBUG)
    probe = "probe-user-7c1f"

    client.post(LOGIN, json={"username": probe, "password": WRONG})
    client.post(LOGIN, json={"username": "asha", "password": WRONG})
    client.post(LOGIN, json={"username": "asha", "password": credentials["asha"]})

    for text_value in (probe, "asha", WRONG, credentials["asha"]):
        assert text_value not in caplog.text
