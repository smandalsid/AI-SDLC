import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from .perf_support import (
    BUS_COUNT,
    MEASURED_CALLS,
    SEEDED_BEFORE_WRITES,
    STORED_BOOKINGS,
    WARM_UP_CALLS,
    stored_bookings,
    threshold,
    timed_ms,
    within_limit,
    write_plan,
)

pytestmark = [pytest.mark.perf, pytest.mark.usefixtures("signed_in")]


@pytest.fixture
def stored_1000(session_factory: sessionmaker[Session]) -> None:
    stored_bookings(session_factory, STORED_BOOKINGS)


@pytest.mark.usefixtures("stored_1000")
def test_bus_detail_p95_is_under_the_read_limit(client: TestClient) -> None:
    def read(index: int) -> float:
        bus_id = index % BUS_COUNT + 1
        return timed_ms(lambda: client.get(f"/api/v1/buses/{bus_id}").status_code, 200)

    def measure() -> list[float]:
        for index in range(WARM_UP_CALLS):
            read(index)
        return [read(index) for index in range(MEASURED_CALLS)]

    limit = threshold("READ_P95_MS")
    observed = within_limit(measure, limit)

    assert observed < limit, f"read p95 {observed:.1f} ms is not under {limit:g} ms"


def test_six_seat_booking_p95_is_under_the_write_limit(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    stored_bookings(session_factory, SEEDED_BEFORE_WRITES)
    with session_factory() as session:
        baseline = int(session.execute(text("SELECT MAX(id) FROM bookings")).scalar_one())
    plan = write_plan()
    assert len(plan) >= WARM_UP_CALLS + MEASURED_CALLS

    def write(index: int) -> float:
        bus_id, seats = plan[index]
        payload = {"bus_id": bus_id, "seat_numbers": seats}
        return timed_ms(lambda: client.post("/api/v1/bookings", json=payload).status_code, 201)

    def measure() -> list[float]:
        with session_factory() as session:
            session.execute(
                text("DELETE FROM bookings WHERE id > :baseline"), {"baseline": baseline}
            )
            session.commit()
        for index in range(WARM_UP_CALLS):
            write(index)
        return [write(index) for index in range(WARM_UP_CALLS, WARM_UP_CALLS + MEASURED_CALLS)]

    limit = threshold("WRITE_P95_MS")
    observed = within_limit(measure, limit)

    assert observed < limit, f"write p95 {observed:.1f} ms is not under {limit:g} ms"
