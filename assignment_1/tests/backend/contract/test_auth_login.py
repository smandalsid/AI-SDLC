import logging
from collections.abc import Mapping
from datetime import datetime

import pytest
from app.core.tokens import get_token_codec
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

LOGIN = "/api/v1/auth/login"
GENERIC_401 = {"error": {"code": "invalid_credentials", "message": "Invalid username or password."}}


def sign_in(client: TestClient, username: str, password: str) -> Response:
    return client.post(LOGIN, json={"username": username, "password": password})


def count_rows(factory: sessionmaker[Session], table: str) -> int:
    with factory() as session:
        return int(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())  # noqa: S608


def test_a_matching_pair_returns_200_with_a_token_and_only_the_user(
    client: TestClient, credentials: Mapping[str, str]
) -> None:
    response = sign_in(client, "asha", credentials["asha"])

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type", "expires_at", "user"}
    assert body["token_type"] == "bearer"
    assert body["expires_at"] == "2026-01-15T11:00:00Z"
    assert body["user"] == {"id": 1, "name": "Asha"}
    assert credentials["asha"] not in response.text
    assert "argon2" not in response.text


def test_the_sign_in_stores_one_session_matching_the_token_and_the_expiry(
    client: TestClient, session_factory: sessionmaker[Session], credentials: Mapping[str, str]
) -> None:
    response = sign_in(client, "asha", credentials["asha"])

    with session_factory() as session:
        rows = session.execute(
            text("SELECT id, user_id, started_at, expires_at, ended_at FROM sessions")
        ).all()
    assert len(rows) == 1
    session_id, user_id, started_at, expires_at, ended_at = rows[0]
    assert get_token_codec().decode(response.json()["access_token"]).session_id == session_id
    assert user_id == 1
    assert (started_at, expires_at, ended_at) == (
        datetime(2026, 1, 15, 10, 30),
        datetime(2026, 1, 15, 11, 0),
        None,
    )


def test_two_sign_ins_create_two_independent_sessions(
    client: TestClient, session_factory: sessionmaker[Session], credentials: Mapping[str, str]
) -> None:
    first = sign_in(client, "asha", credentials["asha"]).json()["access_token"]
    second = sign_in(client, "asha", credentials["asha"]).json()["access_token"]

    assert first != second
    assert count_rows(session_factory, "sessions") == 2
    codec = get_token_codec()
    assert codec.decode(first).session_id != codec.decode(second).session_id


# (username as typed, whose password is sent; None = a wrong password)
REJECTED = [
    pytest.param("asha", None, id="wrong-password"),
    pytest.param("nobody", "asha", id="unknown-username"),
    pytest.param("ravi", "asha", id="other-users-password"),
    pytest.param("ASHA", "asha", id="upper-case-username"),
    pytest.param(" asha", "asha", id="leading-space"),
    pytest.param("asha ", "asha", id="trailing-space"),
    pytest.param("asha' OR '1'='1", "asha", id="sql-injection-text"),
]


def test_every_rejected_attempt_gets_the_same_401_and_stores_no_session(
    client: TestClient, session_factory: sessionmaker[Session], credentials: Mapping[str, str]
) -> None:
    seen = []
    for case in REJECTED:
        username, owner = case.values
        password = "not-the-password" if owner is None else credentials[str(owner)]
        response = sign_in(client, str(username), password)
        assert response.status_code == 401
        assert response.json() == GENERIC_401
        seen.append((response.status_code, response.text, sorted(response.headers.items())))

    assert all(entry == seen[0] for entry in seen)
    assert count_rows(session_factory, "sessions") == 0


INVALID_BODIES = [
    pytest.param({"username": "", "password": "x"}, id="empty-username"),
    pytest.param({"username": "asha", "password": ""}, id="empty-password"),
    pytest.param({"password": "x"}, id="missing-username"),
    pytest.param({"username": "asha"}, id="missing-password"),
    pytest.param({"username": "u" * 51, "password": "x"}, id="long-username"),
    pytest.param({"username": "asha", "password": "x" * 129}, id="long-password"),
    pytest.param({"username": "asha", "password": "x", "extra": 1}, id="extra-field"),
    pytest.param({"username": 5, "password": "x"}, id="non-string"),
]


@pytest.mark.parametrize("body", INVALID_BODIES)
def test_an_invalid_body_returns_422_and_stores_nothing(
    client: TestClient, session_factory: sessionmaker[Session], body: dict[str, object]
) -> None:
    response = client.post(LOGIN, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "x" * 129 not in response.text
    assert count_rows(session_factory, "sessions") == 0
    assert count_rows(session_factory, "sign_in_attempts") == 0


def test_a_body_that_is_not_json_returns_422_and_stores_nothing(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    response = client.post(LOGIN, content=b"not json", headers={"content-type": "application/json"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert count_rows(session_factory, "sessions") == 0


def test_the_password_never_appears_in_responses_logs_or_the_url(
    client: TestClient, credentials: Mapping[str, str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    wrong = "wrong-" + credentials["asha"]

    responses = [sign_in(client, "asha", credentials["asha"]), sign_in(client, "asha", wrong)]

    assert [response.status_code for response in responses] == [200, 401]
    for response in responses:
        for secret in (credentials["asha"], wrong):
            assert secret not in response.text
            assert secret not in str(response.headers)
            assert secret not in str(response.request.url)
    assert credentials["asha"] not in caplog.text
    assert wrong not in caplog.text
