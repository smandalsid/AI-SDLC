from collections.abc import Callable
from typing import NoReturn

import pytest
from app.core.config import Settings
from app.db.session import get_session
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

API = "/api/v1"
NO_STORE = "no-store"


def failing_session() -> NoReturn:
    raise OperationalError("SELECT 1", {}, Exception("login failed on db-host.internal"))


@pytest.mark.parametrize("path", ["/health", "/health/ready"])
def test_the_health_checks_carry_no_store(client: TestClient, path: str) -> None:
    assert client.get(f"{API}{path}").headers["cache-control"] == NO_STORE


def test_a_200_carries_no_store(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    response = client.get(f"{API}/buses", headers=auth_headers("asha"))

    assert response.status_code == 200
    assert response.headers["cache-control"] == NO_STORE


def test_the_login_response_carries_no_store(client: TestClient) -> None:
    response = client.post(f"{API}/auth/login", json={"username": "asha", "password": "x"})

    assert response.status_code == 401
    assert response.headers["cache-control"] == NO_STORE


def test_a_gate_401_carries_no_store(client: TestClient) -> None:
    response = client.get(f"{API}/buses")

    assert response.status_code == 401
    assert response.headers["cache-control"] == NO_STORE


def test_a_404_carries_no_store(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    response = client.get(f"{API}/buses/99", headers=auth_headers("asha"))

    assert response.status_code == 404
    assert response.headers["cache-control"] == NO_STORE


def test_an_unmatched_path_carries_no_store(client: TestClient) -> None:
    response = client.get(f"{API}/nowhere")

    assert response.status_code == 404
    assert response.headers["cache-control"] == NO_STORE


def test_a_422_carries_no_store(
    client: TestClient, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    response = client.post(f"{API}/bookings", json={"bus_id": "x"}, headers=auth_headers("asha"))

    assert response.status_code == 422
    assert response.headers["cache-control"] == NO_STORE


def test_a_503_carries_no_store(app: FastAPI, client: TestClient) -> None:
    app.dependency_overrides[get_session] = failing_session

    response = client.get(f"{API}/health/ready")

    assert response.status_code == 503
    assert response.headers["cache-control"] == NO_STORE


def test_the_preflight_from_the_configured_origin_allows_the_authorization_header(
    client: TestClient, settings: Settings
) -> None:
    origin = settings.cors_origin_list[0]

    response = client.options(
        f"{API}/bookings",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_the_preflight_from_another_origin_is_refused(client: TestClient) -> None:
    response = client.options(
        f"{API}/bookings",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
