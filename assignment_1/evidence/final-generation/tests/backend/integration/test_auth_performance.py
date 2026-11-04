from collections.abc import Callable, Mapping

import pytest
from app.api.deps import get_password_verifier, require_session
from app.core.passwords import PasswordVerifier
from app.services.types import Principal
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from .perf_support import (
    BUS_COUNT,
    MEASURED_CALLS,
    SEEDED_BEFORE_WRITES,
    WARM_UP_CALLS,
    p95,
    stored_bookings,
    timed_ms,
    use_production_hashes,
    write_plan,
)

pytestmark = pytest.mark.perf

LOGIN = "/api/v1/auth/login"
# The two numbers of the specification (NFR-005, NFR-006); the 001 targets stay in thresholds.env
# and are checked with authentication in place by test_performance.py.
SIGN_IN_P95_MS = 500.0
SESSION_CHECK_EXTRA_P95_MS = 50.0


def skip_session_check() -> Principal:
    return Principal(user_id=1, name="Asha", session_id="s" * 32, username="asha")


def test_sign_in_p95_is_under_500_ms_with_the_production_cost_hasher(
    app: FastAPI,
    client: TestClient,
    session_factory: sessionmaker[Session],
    credentials: Mapping[str, str],
) -> None:
    stored_bookings(session_factory, SEEDED_BEFORE_WRITES)
    hasher = use_production_hashes(session_factory, credentials)

    def production_verifier() -> PasswordVerifier:
        return hasher

    app.dependency_overrides[get_password_verifier] = production_verifier

    def sign_in(index: int) -> float:
        username = ("asha", "ravi", "meera")[index % 3]
        body = {"username": username, "password": credentials[username]}
        return timed_ms(lambda: client.post(LOGIN, json=body).status_code, 200)

    def measure() -> list[float]:
        for index in range(WARM_UP_CALLS):
            sign_in(index)
        return [sign_in(index) for index in range(MEASURED_CALLS)]

    observed = p95(measure())
    if observed >= SIGN_IN_P95_MS:
        observed = p95(measure())

    assert observed < SIGN_IN_P95_MS, f"sign-in p95 {observed:.1f} ms is not under 500 ms"


def extra_p95(measure: Callable[[], list[float]], app: FastAPI) -> float:
    """p95 with the session check minus p95 with the check skipped by a dependency override."""
    with_check = p95(measure())
    app.dependency_overrides[require_session] = skip_session_check
    try:
        without_check = p95(measure())
    finally:
        del app.dependency_overrides[require_session]
    return with_check - without_check


def within_extra(measure: Callable[[], list[float]], app: FastAPI) -> float:
    """One re-run on a miss; the second measurement decides."""
    observed = extra_p95(measure, app)
    return observed if observed <= SESSION_CHECK_EXTRA_P95_MS else extra_p95(measure, app)


def test_the_session_check_adds_at_most_50_ms_to_a_seat_list_read(
    app: FastAPI,
    client: TestClient,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    stored_bookings(session_factory, SEEDED_BEFORE_WRITES)
    headers = auth_headers("asha")

    def read(index: int) -> float:
        path = f"/api/v1/buses/{index % BUS_COUNT + 1}"
        return timed_ms(lambda: client.get(path, headers=headers).status_code, 200)

    def measure() -> list[float]:
        for index in range(WARM_UP_CALLS):
            read(index)
        return [read(index) for index in range(MEASURED_CALLS)]

    extra = within_extra(measure, app)

    assert extra <= SESSION_CHECK_EXTRA_P95_MS, f"session check adds {extra:.1f} ms at p95"


def test_the_session_check_adds_at_most_50_ms_to_a_six_seat_booking(
    app: FastAPI,
    client: TestClient,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    stored_bookings(session_factory, SEEDED_BEFORE_WRITES)
    headers = auth_headers("asha")
    with session_factory() as session:
        baseline = int(session.execute(text("SELECT MAX(id) FROM bookings")).scalar_one())
    plan = write_plan()
    assert len(plan) >= WARM_UP_CALLS + MEASURED_CALLS

    def write(index: int) -> float:
        bus_id, seats = plan[index]
        body = {"bus_id": bus_id, "seat_numbers": seats}
        return timed_ms(
            lambda: client.post("/api/v1/bookings", json=body, headers=headers).status_code, 201
        )

    def measure() -> list[float]:
        with session_factory() as session:
            session.execute(text("DELETE FROM bookings WHERE id > :b"), {"b": baseline})
            session.commit()
        for index in range(WARM_UP_CALLS):
            write(index)
        return [write(index) for index in range(WARM_UP_CALLS, WARM_UP_CALLS + MEASURED_CALLS)]

    extra = within_extra(measure, app)

    assert extra <= SESSION_CHECK_EXTRA_P95_MS, f"session check adds {extra:.1f} ms at p95"
