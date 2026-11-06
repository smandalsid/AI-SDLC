from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from app.api.deps import get_clock
from app.core.clock import Clock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
UNAUTHENTICATED = {"error": {"code": "unauthenticated", "message": "Authentication required."}}


class MovableClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current


def use_clock(app: FastAPI, current: datetime) -> MovableClock:
    clock = MovableClock(current)

    def provide() -> Clock:
        return clock

    app.dependency_overrides[get_clock] = provide
    return clock


def session_rows(factory: sessionmaker[Session]) -> list[tuple[int, datetime | None]]:
    with factory() as session:
        rows = session.execute(
            text("SELECT user_id, ended_at FROM sessions ORDER BY started_at, id")
        )
        return [(int(row[0]), row[1]) for row in rows]


def test_a_valid_session_gets_204_with_an_empty_body(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    response = client.post(LOGOUT, headers=auth_headers("asha"))

    assert response.status_code == 204
    assert response.content == b""


def test_without_a_session_the_answer_is_401(client: TestClient) -> None:
    response = client.post(LOGOUT)

    assert response.status_code == 401
    assert response.json() == UNAUTHENTICATED
    assert response.headers["www-authenticate"] == "Bearer"


def test_a_second_logout_with_the_same_token_is_401(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    headers = auth_headers("asha")
    client.post(LOGOUT, headers=headers)

    second = client.post(LOGOUT, headers=headers)

    assert second.status_code == 401
    assert second.json() == UNAUTHENTICATED


def test_the_session_row_is_ended_at_the_clock_time_of_the_sign_out(
    app: FastAPI,
    client: TestClient,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    clock = use_clock(app, datetime(2026, 1, 15, 10, 30, tzinfo=UTC))
    headers = auth_headers("asha")
    clock.current = datetime(2026, 1, 15, 10, 35, tzinfo=UTC)

    client.post(LOGOUT, headers=headers)

    assert session_rows(session_factory) == [(1, datetime(2026, 1, 15, 10, 35))]


def test_the_old_token_is_refused_by_every_protected_route_afterwards(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    headers = auth_headers("asha")
    client.post(LOGOUT, headers=headers)

    responses = [client.get(ME, headers=headers), client.get("/api/v1/buses", headers=headers)]

    assert [response.status_code for response in responses] == [401, 401]
    assert all(response.json() == UNAUTHENTICATED for response in responses)


def test_only_the_current_session_ends_and_a_second_session_of_the_user_stays_valid(
    client: TestClient,
    session_factory: sessionmaker[Session],
    sign_in: Callable[[str], Response],
) -> None:
    first = {"Authorization": f"Bearer {sign_in('asha').json()['access_token']}"}
    second = {"Authorization": f"Bearer {sign_in('asha').json()['access_token']}"}

    client.post(LOGOUT, headers=first)

    assert client.get(ME, headers=first).status_code == 401
    assert client.get(ME, headers=second).status_code == 200
    ended = [row[1] is not None for row in session_rows(session_factory)]
    assert sorted(ended) == [False, True]


def test_another_users_session_is_not_ended(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    asha, ravi = auth_headers("asha"), auth_headers("ravi")

    assert client.post(LOGOUT, headers=asha).status_code == 204

    assert client.get(ME, headers=ravi).status_code == 200


def test_the_sign_out_is_recorded_once_with_the_username_and_the_clock_time(
    app: FastAPI,
    client: TestClient,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    clock = use_clock(app, datetime(2026, 1, 15, 10, 30, tzinfo=UTC))
    headers = auth_headers("asha")
    clock.current += timedelta(minutes=2)

    client.post(LOGOUT, headers=headers)

    with session_factory() as session:
        rows = session.execute(
            text(
                "SELECT username, outcome, attempted_at FROM sign_in_attempts "
                "WHERE outcome = 'signout'"
            )
        ).all()
    assert [tuple(row) for row in rows] == [("asha", "signout", datetime(2026, 1, 15, 10, 32))]


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_other_methods_on_the_logout_address_are_not_allowed_signed_in(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]], method: str
) -> None:
    response = client.request(method, LOGOUT, headers=auth_headers("asha"))

    assert response.status_code == 405
