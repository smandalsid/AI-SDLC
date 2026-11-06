from collections.abc import Callable
from datetime import datetime, timedelta

import pytest
from app.api.deps import get_clock
from app.core.clock import Clock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from ..conftest import FakeClock

API = "/api/v1"
UNAUTHENTICATED = {"error": {"code": "unauthenticated", "message": "Authentication required."}}
EXPIRED_AFTER = timedelta(minutes=31)
PROTECTED = [
    pytest.param("GET", "/buses", id="list-buses"),
    pytest.param("GET", "/buses/1", id="bus-detail"),
    pytest.param("POST", "/bookings", id="create-booking"),
    pytest.param("GET", "/auth/me", id="me"),
    pytest.param("POST", "/auth/logout", id="logout"),
]
COUNTS = text(
    "SELECT (SELECT COUNT(*) FROM bookings), (SELECT COUNT(*) FROM sessions), "
    "(SELECT COUNT(*) FROM sign_in_attempts)"
)


def counts(factory: sessionmaker[Session]) -> tuple[int, int, int]:
    with factory() as session:
        first, second, third = session.execute(COUNTS).one()
    return int(first), int(second), int(third)


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_after_31_minutes_every_protected_route_returns_401_and_changes_nothing(
    client: TestClient,
    fake_clock: FakeClock,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
    method: str,
    path: str,
) -> None:
    headers = auth_headers("asha")
    fake_clock.current += EXPIRED_AFTER
    before = counts(session_factory)

    response = client.request(method, f"{API}{path}", headers=headers, json=None)

    assert response.status_code == 401
    assert response.json() == UNAUTHENTICATED
    assert counts(session_factory) == before


def test_a_booking_sent_after_expiry_returns_401_and_stores_nothing(
    client: TestClient,
    fake_clock: FakeClock,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers("asha")
    fake_clock.current += EXPIRED_AFTER

    response = client.post(
        f"{API}/bookings", json={"bus_id": 1, "seat_numbers": [3]}, headers=headers
    )

    assert response.status_code == 401
    assert counts(session_factory)[0] == 0


def test_signing_in_again_after_expiry_returns_a_fresh_working_token(
    client: TestClient, fake_clock: FakeClock, sign_in: Callable[[str], Response]
) -> None:
    old = {"Authorization": f"Bearer {sign_in('asha').json()['access_token']}"}
    fake_clock.current += EXPIRED_AFTER

    fresh_response = sign_in("asha")
    fresh = {"Authorization": f"Bearer {fresh_response.json()['access_token']}"}

    assert fresh_response.status_code == 200
    assert fresh != old
    assert client.get(f"{API}/auth/me", headers=fresh).status_code == 200
    assert client.get(f"{API}/auth/me", headers=old).status_code == 401


def test_the_session_is_still_valid_just_before_thirty_minutes_and_use_does_not_extend_it(
    client: TestClient,
    fake_clock: FakeClock,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers("asha")

    fake_clock.current += timedelta(minutes=29, seconds=59)
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 200

    fake_clock.current += timedelta(seconds=2)
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401


class FlipClock:
    """Reads one time for the first call of a request and another for every later call."""

    def __init__(self, first: datetime, later: datetime) -> None:
        self.first, self.later, self.calls = first, later, 0

    def now(self) -> datetime:
        self.calls += 1
        return self.first if self.calls == 1 else self.later


def test_a_booking_that_meets_the_expiry_is_stored_whole_or_refused_with_nothing_stored(
    app: FastAPI,
    client: TestClient,
    fake_clock: FakeClock,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers("asha")
    expires = fake_clock.current + timedelta(minutes=30)
    flip = FlipClock(expires - timedelta(seconds=1), expires + timedelta(seconds=1))

    def provide() -> Clock:
        return flip

    app.dependency_overrides[get_clock] = provide
    body = {"bus_id": 1, "seat_numbers": [3, 4]}

    decided_before = client.post(f"{API}/bookings", json=body, headers=headers)
    decided_after = client.post(
        f"{API}/bookings", json={"bus_id": 1, "seat_numbers": [5]}, headers=headers
    )

    assert decided_before.status_code == 201
    assert len(decided_before.json()["bookings"]) == 2
    assert decided_after.status_code == 401
    assert counts(session_factory)[0] == 2
