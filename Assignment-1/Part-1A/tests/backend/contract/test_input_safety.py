import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, inspect, text

INJECTIONS = [
    "1; DROP TABLE bookings;--",
    "1 OR 1=1",
    "' OR '1'='1",
    "1; UPDATE buses SET total_seats = 1",
]


COUNTS = text(
    "SELECT (SELECT COUNT(*) FROM buses), (SELECT COUNT(*) FROM users), "
    "(SELECT COUNT(*) FROM bookings)"
)


def table_state(engine: Engine) -> tuple[set[str], int, int, int]:
    with engine.connect() as connection:
        buses, users, bookings = connection.execute(COUNTS).one()
    return set(inspect(engine).get_table_names()), int(buses), int(users), int(bookings)


@pytest.mark.parametrize("payload", INJECTIONS)
@pytest.mark.parametrize("field", ["bus_id", "user_id"])
def test_injection_text_in_an_identifier_is_rejected_and_changes_nothing(
    client: TestClient, engine: Engine, field: str, payload: str
) -> None:
    before = table_state(engine)
    body: dict[str, object] = {"bus_id": 1, "user_id": 1, "seat_numbers": [3]}
    body[field] = payload

    response = client.post("/api/v1/bookings", json=body)

    assert response.status_code == 422
    assert table_state(engine) == before


@pytest.mark.parametrize("payload", INJECTIONS)
def test_injection_text_as_a_seat_number_is_rejected_and_changes_nothing(
    client: TestClient, engine: Engine, payload: str
) -> None:
    before = table_state(engine)

    response = client.post(
        "/api/v1/bookings", json={"bus_id": 1, "user_id": 1, "seat_numbers": [payload]}
    )

    assert response.status_code == 422
    assert table_state(engine) == before


@pytest.mark.parametrize("payload", INJECTIONS)
def test_injection_text_in_the_path_is_rejected_and_changes_nothing(
    client: TestClient, engine: Engine, payload: str
) -> None:
    before = table_state(engine)

    response = client.get(f"/api/v1/buses/{payload}")

    assert response.status_code in (404, 422)
    assert set(response.json()) == {"error"}
    assert table_state(engine) == before


def test_error_bodies_do_not_echo_the_submitted_text(client: TestClient) -> None:
    response = client.post(
        "/api/v1/bookings",
        json={"bus_id": INJECTIONS[0], "user_id": 1, "seat_numbers": [3]},
    )

    assert "DROP TABLE" not in json.dumps(response.json())
