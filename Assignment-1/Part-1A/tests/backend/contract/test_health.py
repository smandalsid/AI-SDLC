from typing import NoReturn

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_session


def failing_session() -> NoReturn:
    raise OperationalError("SELECT 1", {}, Exception("login failed on db-host.internal"))


def test_liveness_is_ok_even_when_the_database_dependency_fails(
    app: FastAPI, client: TestClient
) -> None:
    app.dependency_overrides[get_session] = failing_session

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_is_ok_against_the_test_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_503_without_leaking_details_when_the_database_fails(
    app: FastAPI, client: TestClient
) -> None:
    app.dependency_overrides[get_session] = failing_session

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "service_unavailable"
    assert isinstance(body["error"]["message"], str)
    for marker in ("SELECT", "db-host.internal", "OperationalError", "login failed"):
        assert marker not in response.text
