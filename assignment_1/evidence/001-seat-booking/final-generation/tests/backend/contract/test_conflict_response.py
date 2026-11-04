from fastapi.testclient import TestClient

BODY = {"bus_id": 1, "user_id": 1, "seat_numbers": [5]}


def test_the_409_body_has_the_shared_shape_and_hides_database_details(
    client: TestClient,
) -> None:
    client.post("/api/v1/bookings", json=BODY)

    response = client.post("/api/v1/bookings", json={**BODY, "user_id": 2})

    assert response.status_code == 409
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == "seat_unavailable"
    for fragment in ("UQ_bookings", "INSERT", "duplicate", "Violation", "constraint", "bookings"):
        assert fragment.lower() not in response.text.lower()
