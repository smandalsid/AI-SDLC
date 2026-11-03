from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

BOOKINGS = "/api/v1/bookings"
VALID = {"bus_id": 1, "user_id": 1, "seat_numbers": [3, 4]}


def stored_bookings(factory: sessionmaker[Session]) -> list[tuple[int, int, int, datetime]]:
    with factory() as session:
        rows = session.execute(
            text("SELECT bus_id, user_id, seat_number, booked_at FROM bookings ORDER BY id")
        ).all()
    return [(int(r[0]), int(r[1]), int(r[2]), r[3]) for r in rows]


def assert_error(response_json: dict[str, Any], code: str) -> None:
    assert set(response_json) == {"error"}
    assert response_json["error"]["code"] == code


def test_booking_two_seats_returns_201_with_one_shared_utc_timestamp(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    response = client.post(BOOKINGS, json=VALID)

    assert response.status_code == 201
    bookings = response.json()["bookings"]
    assert [b["id"] for b in bookings] == [1, 2]
    assert [(b["bus_id"], b["user_id"], b["seat_number"]) for b in bookings] == [
        (1, 1, 3),
        (1, 1, 4),
    ]
    assert {b["booked_at"] for b in bookings} == {"2026-01-15T10:30:00Z"}
    assert all(set(b) == {"id", "bus_id", "user_id", "seat_number", "booked_at"} for b in bookings)


def test_one_row_per_seat_is_stored_with_the_server_time(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    client.post(BOOKINGS, json=VALID)

    rows = stored_bookings(session_factory)
    assert [row[:3] for row in rows] == [(1, 1, 3), (1, 1, 4)]
    assert {row[3] for row in rows} == {datetime(2026, 1, 15, 10, 30)}


def test_six_seats_are_accepted(client: TestClient) -> None:
    payload = {**VALID, "seat_numbers": [1, 2, 3, 4, 5, 6]}

    response = client.post(BOOKINGS, json=payload)

    assert response.status_code == 201
    assert len(response.json()["bookings"]) == 6


@pytest.mark.parametrize(
    "seats",
    [[], [3, 3], [1, 2, 3, 4, 5, 6, 7], [0], [-1], [99999999999999999999], ["3"], [3.5], [True]],
)
def test_invalid_seat_lists_are_rejected_with_422_and_store_nothing(
    client: TestClient, session_factory: sessionmaker[Session], seats: list[Any]
) -> None:
    response = client.post(BOOKINGS, json={**VALID, "seat_numbers": seats})

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")
    assert stored_bookings(session_factory) == []


@pytest.mark.parametrize(
    "payload",
    [
        {**VALID, "booked_at": "2026-01-01T00:00:00Z"},
        {**VALID, "unexpected": 1},
        {**VALID, "bus_id": "1"},
        {**VALID, "user_id": 1.5},
        {**VALID, "bus_id": 0},
        {**VALID, "user_id": -3},
        {**VALID, "bus_id": 99999999999999999999},
        {**VALID, "user_id": 99999999999999999999},
        {"user_id": 1, "seat_numbers": [3]},
        {"bus_id": 1, "seat_numbers": [3]},
        {"bus_id": 1, "user_id": 1},
    ],
)
def test_invalid_bodies_are_rejected_with_422_and_store_nothing(
    client: TestClient, session_factory: sessionmaker[Session], payload: dict[str, Any]
) -> None:
    response = client.post(BOOKINGS, json=payload)

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")
    assert stored_bookings(session_factory) == []


@pytest.mark.parametrize("seat", [21, 2147483647])
def test_a_seat_beyond_the_bus_is_rejected_with_400(
    client: TestClient, session_factory: sessionmaker[Session], seat: int
) -> None:
    response = client.post(BOOKINGS, json={**VALID, "seat_numbers": [3, seat]})

    assert response.status_code == 400
    assert_error(response.json(), "invalid_seat")
    assert stored_bookings(session_factory) == []


def test_unknown_bus_is_rejected_with_404(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    response = client.post(BOOKINGS, json={**VALID, "bus_id": 99})

    assert response.status_code == 404
    assert_error(response.json(), "bus_not_found")
    assert stored_bookings(session_factory) == []


def test_unknown_user_is_rejected_with_404(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    response = client.post(BOOKINGS, json={**VALID, "user_id": 99})

    assert response.status_code == 404
    assert_error(response.json(), "user_not_found")
    assert stored_bookings(session_factory) == []
