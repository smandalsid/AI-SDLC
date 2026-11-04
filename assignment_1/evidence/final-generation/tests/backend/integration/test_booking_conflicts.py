import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

BOOKINGS = "/api/v1/bookings"
SIMULTANEOUS_REQUESTS = 20

pytestmark = pytest.mark.usefixtures("signed_in")


def book(
    client: TestClient,
    seats: list[int],
    bus_id: int = 1,
    headers: dict[str, str] | None = None,
) -> Response:
    return client.post(BOOKINGS, json={"bus_id": bus_id, "seat_numbers": seats}, headers=headers)


def stored(factory: sessionmaker[Session]) -> list[tuple[int, int, int]]:
    with factory() as session:
        rows = session.execute(
            text("SELECT bus_id, user_id, seat_number FROM bookings ORDER BY id")
        ).all()
    return [(int(r[0]), int(r[1]), int(r[2])) for r in rows]


def test_second_booking_of_a_seat_returns_409_and_changes_nothing(
    client: TestClient,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    assert book(client, [7]).status_code == 201
    before = stored(session_factory)

    response = book(client, [7], headers=auth_headers("ravi"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "seat_unavailable"
    assert stored(session_factory) == before == [(1, 1, 7)]


def test_one_taken_seat_stores_none_of_the_requested_seats(
    client: TestClient,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    book(client, [7])

    response = book(client, [8, 9, 7], headers=auth_headers("ravi"))

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
    client: TestClient,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    book(client, [7], bus_id=1)

    response = book(client, [7], bus_id=2, headers=auth_headers("ravi"))

    assert response.status_code == 201
    assert stored(session_factory) == [(1, 1, 7), (2, 2, 7)]


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"bus_id": 1, "seat_numbers": [3]}, 409),
        ({"bus_id": 1, "seat_numbers": [4, 21]}, 400),
        ({"bus_id": 99, "seat_numbers": [4]}, 404),
        ({"bus_id": 1, "user_id": 2, "seat_numbers": [4]}, 422),
        ({"bus_id": 1, "seat_numbers": [4, 4]}, 422),
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
    app: FastAPI,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    barrier = threading.Barrier(SIMULTANEOUS_REQUESTS)
    headers = auth_headers("asha")

    def attempt(_: int) -> int:
        own_client = TestClient(app, raise_server_exceptions=False, headers=headers)
        barrier.wait()
        return int(book(own_client, [10]).status_code)

    with ThreadPoolExecutor(max_workers=SIMULTANEOUS_REQUESTS) as pool:
        codes = list(pool.map(attempt, range(SIMULTANEOUS_REQUESTS)))

    assert sorted(codes) == [201] + [409] * (SIMULTANEOUS_REQUESTS - 1)
    assert stored(session_factory) == [(1, 1, 10)]


def test_two_signed_in_users_book_different_seats_at_once_each_under_their_own_id(
    app: FastAPI,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    barrier = threading.Barrier(2)
    seats = {"asha": [11], "ravi": [12]}
    headers = {name: auth_headers(name) for name in seats}

    def attempt(name: str) -> int:
        own_client = TestClient(app, raise_server_exceptions=False, headers=headers[name])
        barrier.wait()
        return int(book(own_client, seats[name]).status_code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(attempt, seats))

    assert codes == [201, 201]
    assert sorted(stored(session_factory)) == [(1, 1, 11), (1, 2, 12)]


def test_the_same_seat_booked_at_once_by_two_users_gives_one_booking_and_one_conflict(
    app: FastAPI,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    barrier = threading.Barrier(2)
    headers = {name: auth_headers(name) for name in ("asha", "ravi")}

    def attempt(name: str) -> int:
        own_client = TestClient(app, raise_server_exceptions=False, headers=headers[name])
        barrier.wait()
        return int(book(own_client, [13]).status_code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(attempt, headers))

    assert sorted(codes) == [201, 409]
    assert len(stored(session_factory)) == 1
