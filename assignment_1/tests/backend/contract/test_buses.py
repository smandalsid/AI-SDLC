import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


def add_booking(factory: sessionmaker[Session], bus_id: int, seat: int) -> None:
    with factory() as session:
        session.execute(
            text(
                "INSERT INTO bookings (bus_id, user_id, seat_number, booked_at) "
                "VALUES (:bus_id, 1, :seat, SYSUTCDATETIME())"
            ),
            {"bus_id": bus_id, "seat": seat},
        )
        session.commit()


def assert_error(response_json: dict[str, dict[str, str]], code: str) -> None:
    assert set(response_json) == {"error"}
    assert response_json["error"]["code"] == code


def test_list_returns_the_three_seeded_buses(client: TestClient) -> None:
    response = client.get("/api/v1/buses")

    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["page_size"], body["total"]) == (1, 20, 3)
    assert body["items"] == [
        {"id": 1, "name": "Bus A", "total_seats": 20},
        {"id": 2, "name": "Bus B", "total_seats": 30},
        {"id": 3, "name": "Bus C", "total_seats": 40},
    ]


def test_list_honours_the_requested_page_size(client: TestClient) -> None:
    body = client.get("/api/v1/buses?page=2&page_size=2").json()

    assert [bus["id"] for bus in body["items"]] == [3]
    assert (body["page"], body["page_size"], body["total"]) == (2, 2, 3)


def test_page_size_of_100_is_allowed(client: TestClient) -> None:
    assert client.get("/api/v1/buses?page_size=100").status_code == 200


@pytest.mark.parametrize(
    "query", ["page=0", "page=abc", "page=1000001", "page_size=0", "page_size=101"]
)
def test_invalid_paging_is_rejected(client: TestClient, query: str) -> None:
    response = client.get(f"/api/v1/buses?{query}")

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


def test_detail_lists_every_seat_as_available_when_nothing_is_booked(client: TestClient) -> None:
    response = client.get("/api/v1/buses/1")

    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["name"], body["total_seats"]) == (1, "Bus A", 20)
    assert body["seats"] == [{"seat_number": n, "status": "available"} for n in range(1, 21)]


def test_detail_marks_only_the_booked_seat(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    add_booking(session_factory, bus_id=1, seat=5)

    seats = client.get("/api/v1/buses/1").json()["seats"]

    booked = [seat["seat_number"] for seat in seats if seat["status"] == "booked"]
    assert booked == [5]
    assert len(seats) == 20


def test_bookings_on_one_bus_do_not_affect_another(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    add_booking(session_factory, bus_id=1, seat=7)

    seats = client.get("/api/v1/buses/2").json()["seats"]

    assert all(seat["status"] == "available" for seat in seats)
    assert len(seats) == 30


def test_unknown_bus_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/buses/99")

    assert response.status_code == 404
    assert_error(response.json(), "bus_not_found")


@pytest.mark.parametrize("bus_id", ["abc", "0", "-1", "1.5", "99999999999999999999"])
def test_malformed_or_oversized_bus_id_is_rejected_with_422(
    client: TestClient, bus_id: str
) -> None:
    response = client.get(f"/api/v1/buses/{bus_id}")

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")
