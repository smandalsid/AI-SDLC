import pytest
from fastapi.testclient import TestClient


def test_list_returns_the_seeded_users_in_id_order(client: TestClient) -> None:
    response = client.get("/api/v1/users")

    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["page_size"], body["total"]) == (1, 20, 3)
    assert body["items"] == [
        {"id": 1, "name": "Asha"},
        {"id": 2, "name": "Ravi"},
        {"id": 3, "name": "Meera"},
    ]


def test_list_honours_the_requested_page(client: TestClient) -> None:
    body = client.get("/api/v1/users?page=2&page_size=2").json()

    assert [user["name"] for user in body["items"]] == ["Meera"]
    assert (body["page"], body["page_size"], body["total"]) == (2, 2, 3)


def test_page_size_of_100_is_allowed(client: TestClient) -> None:
    assert client.get("/api/v1/users?page_size=100").status_code == 200


@pytest.mark.parametrize(
    "query", ["page=0", "page=abc", "page=1000001", "page_size=0", "page_size=101"]
)
def test_invalid_paging_is_rejected(client: TestClient, query: str) -> None:
    response = client.get(f"/api/v1/users?{query}")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
