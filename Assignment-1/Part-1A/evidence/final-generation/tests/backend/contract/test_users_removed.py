import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

USERS = "/api/v1/users"
NAMES = ("Asha", "Ravi", "Meera", "asha", "ravi", "meera")


def assert_not_found(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    for name in NAMES:
        assert name not in response.text


@pytest.mark.usefixtures("signed_in")
@pytest.mark.parametrize("path", [USERS, f"{USERS}?page=2&page_size=2", f"{USERS}/1"])
def test_the_user_list_is_gone_for_a_signed_in_caller(client: TestClient, path: str) -> None:
    assert_not_found(client, path)


@pytest.mark.parametrize("path", [USERS, f"{USERS}?page=2&page_size=2", f"{USERS}/1"])
def test_the_user_list_is_gone_for_a_signed_out_caller(client: TestClient, path: str) -> None:
    assert_not_found(client, path)


def test_the_users_path_is_absent_from_the_openapi_document(app: FastAPI) -> None:
    paths = app.openapi()["paths"]

    assert not [path for path in paths if path.startswith(USERS)]
