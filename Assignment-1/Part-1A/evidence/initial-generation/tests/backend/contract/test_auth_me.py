from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

ME = "/api/v1/auth/me"


def test_a_valid_session_gets_only_the_id_and_the_name(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    response = client.get(ME, headers=auth_headers("asha"))

    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Asha"}


def test_each_user_sees_their_own_identity(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    assert client.get(ME, headers=auth_headers("ravi")).json() == {"id": 2, "name": "Ravi"}


def test_without_a_session_the_answer_is_401(client: TestClient) -> None:
    response = client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    assert response.headers["www-authenticate"] == "Bearer"


def test_the_name_always_comes_from_the_database(
    client: TestClient,
    session_factory: sessionmaker[Session],
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers("asha")
    with session_factory() as session:
        session.execute(text("UPDATE users SET name = 'Asha Renamed' WHERE id = 1"))
        session.commit()

    assert client.get(ME, headers=headers).json() == {"id": 1, "name": "Asha Renamed"}
