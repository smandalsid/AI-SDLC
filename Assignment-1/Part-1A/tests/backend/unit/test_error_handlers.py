import json
from collections.abc import Callable

import pytest
from app.api.error_handlers import register_error_handlers, response_for
from app.core.errors import (
    AppError,
    BusNotFoundError,
    InvalidCredentialsError,
    InvalidSeatError,
    SeatAlreadyBookedError,
    TooManyAttemptsError,
    UnauthenticatedError,
    UserNotFoundError,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

LEAKY_MARKERS = (
    "Traceback",
    "SELECT",
    "hidden_table",
    "db-host.internal",
    "/Users/someone",
    "secret.py",
    "boom",
)


class Payload(BaseModel):
    seat: int = Field(ge=1)


FACTORIES: dict[str, Callable[[], Exception]] = {
    "invalid_seat": InvalidSeatError,
    "bus_not_found": BusNotFoundError,
    "user_not_found": UserNotFoundError,
    "seat_unavailable": SeatAlreadyBookedError,
    "unauthenticated": UnauthenticatedError,
    "invalid_credentials": InvalidCredentialsError,
    "too_many_attempts": lambda: TooManyAttemptsError(retry_after_seconds=7),
    "db_down": lambda: OperationalError(
        "SELECT secret_column FROM hidden_table", {}, Exception("login failed on db-host.internal")
    ),
    "pool_timeout": lambda: PoolTimeoutError("queue limit reached for db-host.internal"),
    "unexpected": lambda: RuntimeError("boom at /Users/someone/app/secret.py"),
}


def build_client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/raise/{kind}")
    def raise_kind(kind: str) -> None:
        raise FACTORIES[kind]()

    @app.post("/payload")
    def post_payload(payload: Payload) -> dict[str, int]:
        return {"seat": payload.seat}

    return TestClient(app, raise_server_exceptions=False)


def assert_error_shape(body: object, code: str) -> None:
    assert isinstance(body, dict)
    assert set(body) == {"error"}
    error = body["error"]
    assert isinstance(error, dict)
    assert set(error) == {"code", "message"}
    assert error["code"] == code
    assert isinstance(error["message"], str)
    assert error["message"]


@pytest.mark.parametrize(
    ("kind", "status", "code"),
    [
        ("invalid_seat", 400, "invalid_seat"),
        ("bus_not_found", 404, "bus_not_found"),
        ("user_not_found", 404, "user_not_found"),
        ("seat_unavailable", 409, "seat_unavailable"),
        ("unauthenticated", 401, "unauthenticated"),
        ("invalid_credentials", 401, "invalid_credentials"),
        ("too_many_attempts", 429, "too_many_attempts"),
        ("db_down", 503, "service_unavailable"),
        ("pool_timeout", 503, "service_unavailable"),
        ("unexpected", 500, "internal_error"),
    ],
)
def test_each_exception_maps_to_its_status_and_code(kind: str, status: int, code: str) -> None:
    response = build_client().get(f"/raise/{kind}")

    assert response.status_code == status
    assert_error_shape(response.json(), code)


@pytest.mark.parametrize("kind", ["db_down", "pool_timeout", "unexpected"])
def test_server_errors_do_not_leak_internals(kind: str) -> None:
    response = build_client().get(f"/raise/{kind}")

    for marker in LEAKY_MARKERS:
        assert marker not in response.text


def test_validation_errors_use_the_shared_shape_without_echoing_values() -> None:
    client = build_client()

    wrong_type = client.post("/payload", json={"seat": "secret-value-xyz"})
    missing = client.post("/payload", json={})

    for response in (wrong_type, missing):
        assert response.status_code == 422
        assert_error_shape(response.json(), "validation_error")
    assert "secret-value-xyz" not in wrong_type.text


def test_unknown_route_and_wrong_method_use_the_shared_shape() -> None:
    client = build_client()

    not_found = client.get("/nowhere")
    wrong_method = client.get("/payload")

    assert not_found.status_code == 404
    assert_error_shape(not_found.json(), "not_found")
    assert wrong_method.status_code == 405
    assert_error_shape(wrong_method.json(), "method_not_allowed")


def test_unauthenticated_response_carries_the_bearer_challenge() -> None:
    response = build_client().get("/raise/unauthenticated")

    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "error": {"code": "unauthenticated", "message": "Authentication required."}
    }


def test_invalid_credentials_body_is_the_generic_message() -> None:
    response = build_client().get("/raise/invalid_credentials")

    assert response.json() == {
        "error": {"code": "invalid_credentials", "message": "Invalid username or password."}
    }
    assert "www-authenticate" not in response.headers


def test_too_many_attempts_names_the_wait_in_the_message_and_the_retry_after_header() -> None:
    response = build_client().get("/raise/too_many_attempts")

    assert response.headers["retry-after"] == "7"
    assert "7 seconds" in response.json()["error"]["message"]


@pytest.mark.parametrize(
    "kind", ["unauthenticated", "invalid_credentials", "too_many_attempts", "bus_not_found"]
)
def test_response_for_matches_the_registered_handler(kind: str) -> None:
    via_handler = build_client().get(f"/raise/{kind}")
    error = FACTORIES[kind]()
    assert isinstance(error, AppError)
    direct = response_for(error)

    assert direct.status_code == via_handler.status_code
    assert json.loads(bytes(direct.body)) == via_handler.json()
    for header in ("www-authenticate", "retry-after"):
        assert direct.headers.get(header) == via_handler.headers.get(header)


def test_every_unauthenticated_cause_produces_the_identical_response() -> None:
    first = response_for(UnauthenticatedError())
    second = response_for(UnauthenticatedError())

    assert (first.status_code, bytes(first.body)) == (second.status_code, bytes(second.body))
