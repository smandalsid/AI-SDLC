import pytest
from app.api.middleware.auth_gate import public_operations
from app.api.v1.router import public_router
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

API = "/api/v1"
PUBLIC = frozenset(
    {("GET", f"{API}/health"), ("GET", f"{API}/health/ready"), ("POST", f"{API}/auth/login")}
)
FORGED = "Bearer " + "x" * 40


def api_operations(app: FastAPI) -> list[tuple[str, str]]:
    return [
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith(API)
        for method in sorted(route.methods)
    ]


def concrete(path: str) -> str:
    return path.replace("{bus_id}", "1")


def test_the_public_set_is_exactly_the_login_and_the_two_health_checks() -> None:
    assert public_operations(public_router) == PUBLIC


def test_the_walk_covers_every_registered_api_route(app: FastAPI) -> None:
    operations = api_operations(app)

    assert len(operations) >= len(PUBLIC) + 4
    assert PUBLIC <= set(operations)


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": FORGED}], ids=["no-credential", "forged"]
)
def test_only_the_public_operations_accept_an_unauthenticated_call(
    app: FastAPI, client: TestClient, headers: dict[str, str]
) -> None:
    accepted = {
        (method, path)
        for method, path in api_operations(app)
        if client.request(method, concrete(path), headers=headers).status_code != 401
    }

    assert accepted == PUBLIC


def test_a_route_registered_directly_on_the_app_is_protected_by_default(
    app: FastAPI, client: TestClient
) -> None:
    app.add_api_route(f"{API}/added-later", lambda: {"hidden": "data"})

    response = client.get(f"{API}/added-later")

    assert response.status_code == 401
    assert "hidden" not in response.text


def test_users_is_not_reachable_without_a_credential(client: TestClient) -> None:
    response = client.get(f"{API}/users")

    assert response.status_code == 401
    assert "Asha" not in response.text
