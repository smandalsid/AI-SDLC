from collections.abc import Mapping
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

LOGIN = "/api/v1/auth/login"
NOW = datetime(2026, 1, 15, 10, 30)


def attempts(factory: sessionmaker[Session]) -> list[tuple[str, str, datetime]]:
    with factory() as session:
        rows = session.execute(
            text("SELECT username, outcome, attempted_at FROM sign_in_attempts ORDER BY id")
        ).all()
    return [(str(r[0]), str(r[1]), r[2]) for r in rows]


def test_a_successful_sign_in_adds_one_success_row(
    client: TestClient, session_factory: sessionmaker[Session], credentials: Mapping[str, str]
) -> None:
    client.post(LOGIN, json={"username": "asha", "password": credentials["asha"]})

    assert attempts(session_factory) == [("asha", "success", NOW)]


def test_a_failed_sign_in_adds_one_failure_row_that_survives_the_error_response(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    response = client.post(LOGIN, json={"username": "asha", "password": "wrong-password"})

    assert response.status_code == 401
    assert attempts(session_factory) == [("asha", "failure", NOW)]


def test_an_unknown_username_is_recorded_as_typed(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    client.post(LOGIN, json={"username": "Nobody ", "password": "wrong-password"})

    assert attempts(session_factory) == [("Nobody ", "failure", NOW)]


def test_no_row_holds_a_password(
    client: TestClient, session_factory: sessionmaker[Session], credentials: Mapping[str, str]
) -> None:
    wrong = "wrong-" + credentials["asha"]
    client.post(LOGIN, json={"username": "asha", "password": wrong})
    client.post(LOGIN, json={"username": "asha", "password": credentials["asha"]})

    flattened = " ".join(str(value) for row in attempts(session_factory) for value in row)
    assert len(attempts(session_factory)) == 2
    assert wrong not in flattened
    assert credentials["asha"] not in flattened
