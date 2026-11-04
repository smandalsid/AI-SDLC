import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

BOOKINGS = "/api/v1/bookings"
SIMULTANEOUS_REQUESTS = 20


def book(client: TestClient, seats: list[int], bus_id: int = 1, user_id: int = 1) -> Response:
    return client.post(BOOKINGS, json={"bus_id": bus_id, "user_id": user_id, "seat_numbers": seats})


def stored(factory: sessionmaker[Session]) -> list[tuple[int, int, int]]:
    with factory() as session:
        rows = session.execute(
            text("SELECT bus_id, user_id, seat_number FROM bookings ORDER BY id")
        ).all()
    return [(int(r[0]), int(r[1]), int(r[2])) for r in rows]


def test_second_booking_of_a_seat_returns_409_and_changes_nothing(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    assert book(client, [7]).status_code == 201
    before = stored(session_factory)

    response = book(client, [7], user_id=2)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "seat_unavailable"
    assert stored(session_factory) == before == [(1, 1, 7)]


def test_one_taken_seat_stores_none_of_the_requested_seats(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    book(client, [7])

    response = book(client, [8, 9, 7], user_id=2)

    assert response.status_code == 409
    assert stored(session_factory) == [(1, 1, 7)]
    seats = client.get("/api/v1/buses/1").json()["seats"]
    assert {
        seat["seat_number"]: seat["status"] for seat in seats if seat["seat_number"] in (8, 9)
    } == {
        8: "available",
        9: "available",
    }


def test_the_same_seat_number_on_another_bus_is_still_bookable(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    book(client, [7], bus_id=1)

    response = book(client, [7], bus_id=2, user_id=2)

    assert response.status_code == 201
    assert stored(session_factory) == [(1, 1, 7), (2, 2, 7)]


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"bus_id": 1, "user_id": 2, "seat_numbers": [3]}, 409),
        ({"bus_id": 1, "user_id": 2, "seat_numbers": [4, 21]}, 400),
        ({"bus_id": 99, "user_id": 2, "seat_numbers": [4]}, 404),
        ({"bus_id": 1, "user_id": 99, "seat_numbers": [4]}, 404),
        ({"bus_id": 1, "user_id": 2, "seat_numbers": [4, 4]}, 422),
    ],
)
def test_every_kind_of_rejected_request_leaves_the_table_identical(
    client: TestClient,
    session_factory: sessionmaker[Session],
    payload: dict[str, object],
    status: int,
) -> None:
    book(client, [3])
    before = stored(session_factory)

    response = client.post(BOOKINGS, json=payload)

    assert response.status_code == status
    assert stored(session_factory) == before


def test_twenty_simultaneous_requests_book_one_seat_exactly_once(
    app: FastAPI, session_factory: sessionmaker[Session]
) -> None:
    barrier = threading.Barrier(SIMULTANEOUS_REQUESTS)

    def attempt(index: int) -> int:
        own_client = TestClient(app, raise_server_exceptions=False)
        barrier.wait()
        response = book(own_client, [10], user_id=index % 3 + 1)
        return int(response.status_code)

    with ThreadPoolExecutor(max_workers=SIMULTANEOUS_REQUESTS) as pool:
        codes = list(pool.map(attempt, range(SIMULTANEOUS_REQUESTS)))

    assert sorted(codes) == [201] + [409] * (SIMULTANEOUS_REQUESTS - 1)
    rows = stored(session_factory)
    assert len(rows) == 1
    assert rows[0][0] == 1
    assert rows[0][2] == 10
