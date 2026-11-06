"""Health endpoint, the uniform error shape and CORS (Principle IX)."""

from datetime import UTC, datetime

import pytest
from app_helpers import FixedClock, action_dict
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.llm.stub_client import Scripted, StubLLMClient
from app.models.errors import (
    LLMInfrastructureError,
    LLMOutputError,
    PayloadTooLarge,
    RequestValidationFailed,
)
from app.settings import Settings

pytestmark = pytest.mark.covers("GR-5", "FR-8", "FR-14")

NOW = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)


def _client(
    *responses: Scripted, cors: str = "", raise_server_exceptions: bool = False
) -> TestClient:
    settings = Settings(_env_file=None, cors_origins=cors)
    stub = StubLLMClient(*(responses or (action_dict(),)))
    app = create_app(settings=settings, llm_client=stub, clock=FixedClock(NOW))
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _is_uniform(body: dict[str, object]) -> bool:
    error = body.get("error")
    return (
        set(body) == {"error"}
        and isinstance(error, dict)
        and set(error) == {"code", "message"}
        and all(isinstance(v, str) for v in error.values())
    )


@pytest.mark.endpoint("GET", "/api/v1/health", "success")
def test_health_is_ok() -> None:
    response = _client().get("/api/v1/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}


@pytest.mark.endpoint("GET", "/api/v1/health", "failure")
def test_wrong_method_uses_the_uniform_error_body() -> None:
    response = _client().post("/api/v1/health")
    body = response.json()
    assert response.status_code == 405 and _is_uniform(body)
    assert body["error"]["code"] == "method_not_allowed"


def test_unknown_path_uses_the_uniform_error_body() -> None:
    response = _client().get("/api/v1/nothing")
    assert response.status_code == 404 and _is_uniform(response.json())
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.endpoint("POST", "/api/v1/actions", "failure")
def test_schema_errors_are_422_invalid_request() -> None:
    client = _client()
    for body in (
        {"text": 5},
        {"text": "x", "unknown": 1},
        {"text": "x", "timezone": "Mars/Phobos"},
    ):
        response = client.post("/api/v1/actions", json=body)
        assert response.status_code == 422 and _is_uniform(response.json())
        assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.endpoint("POST", "/api/v1/actions", "failure")
def test_an_unexpected_exception_is_a_generic_500_without_internals() -> None:
    client = _client(RuntimeError("secret /etc/private path"))
    response = client.post("/api/v1/actions", json={"text": "remind me"})
    assert response.status_code == 500 and _is_uniform(response.json())
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret" not in response.text and "/etc" not in response.text
    assert "Traceback" not in response.text


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (LLMOutputError("schema", "bad"), 502, "model_output_invalid"),
        (LLMInfrastructureError("timeout", "slow"), 504, "llm_timeout"),
        (LLMInfrastructureError("auth", "no"), 503, "llm_unavailable"),
    ],
)
def test_domain_errors_map_to_their_status_and_code(
    error: Exception, status: int, code: str
) -> None:
    response = _client(error).post("/api/v1/actions", json={"text": "remind me"})
    assert response.status_code == status and _is_uniform(response.json())
    assert response.json()["error"]["code"] == code


def test_the_error_table_matches_the_data_model() -> None:
    table = {
        RequestValidationFailed("x"): (422, "invalid_request"),
        PayloadTooLarge("x"): (413, "payload_too_large"),
        LLMOutputError("schema", "x"): (502, "model_output_invalid"),
    }
    for error, (status, code) in table.items():
        assert (error.http_status, error.code) == (status, code)


def test_cors_is_off_unless_origins_are_configured() -> None:
    response = _client().get("/api/v1/health", headers={"Origin": "http://ok.test"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_only_the_configured_origin() -> None:
    client = _client(cors="http://ok.test")
    allowed = client.get("/api/v1/health", headers={"Origin": "http://ok.test"})
    other = client.get("/api/v1/health", headers={"Origin": "http://evil.test"})
    assert allowed.headers["access-control-allow-origin"] == "http://ok.test"
    assert "access-control-allow-origin" not in other.headers
