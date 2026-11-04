from collections.abc import Callable, Iterator, Mapping

import pytest
from app.core.config import get_settings
from app.core.tokens import get_token_codec
from fastapi import FastAPI
from fastapi.testclient import TestClient

API = "/api/v1"
SETTINGS: list[tuple[str, Mapping[str, str]]] = [
    ("debug-flag", {"DEBUG": "true", "APP_DEBUG": "1"}),
    ("auth-switches", {"AUTH_DISABLED": "true", "DISABLE_AUTH": "1", "BYPASS_AUTH": "1"}),
    ("no-mock-passwords", {"MOCK_USER_PASSWORDS": "{}"}),
    ("unknown-variables", {"ENVIRONMENT": "development", "FEATURE_X": "on", "SKIP_LOGIN": "1"}),
]
# (username, password) pairs a careless build might accept.
DEFAULT_CREDENTIALS = [
    ("", ""),
    ("admin", "admin"),
    ("asha", ""),
    ("asha", "asha"),
    ("test", "test"),
]


@pytest.fixture
def rebuilt(
    monkeypatch: pytest.MonkeyPatch, make_app: Callable[[], FastAPI]
) -> Iterator[Callable[[Mapping[str, str]], TestClient]]:
    """Builds the app after the environment changed; the settings and key caches are reset."""

    def build(environment: Mapping[str, str]) -> TestClient:
        for name, value in environment.items():
            monkeypatch.setenv(name, value)
        get_settings.cache_clear()
        get_token_codec.cache_clear()
        return TestClient(make_app(), raise_server_exceptions=False)

    yield build
    monkeypatch.undo()
    get_settings.cache_clear()
    get_token_codec.cache_clear()


@pytest.mark.parametrize(("label", "environment"), SETTINGS, ids=[label for label, _ in SETTINGS])
def test_unauthenticated_calls_are_refused_whatever_the_environment(
    rebuilt: Callable[[Mapping[str, str]], TestClient],
    label: str,
    environment: Mapping[str, str],
) -> None:
    client = rebuilt(environment)

    responses = [
        client.get(f"{API}/buses"),
        client.get(f"{API}/buses/1"),
        client.post(f"{API}/bookings", json={"bus_id": 1, "seat_numbers": [3]}),
        client.get(f"{API}/auth/me"),
        client.post(f"{API}/auth/logout"),
    ]

    assert [response.status_code for response in responses] == [401] * len(responses)
    assert "Bus A" not in "".join(response.text for response in responses)


@pytest.mark.parametrize(("label", "environment"), SETTINGS, ids=[label for label, _ in SETTINGS])
@pytest.mark.parametrize(("username", "password"), DEFAULT_CREDENTIALS)
def test_no_empty_or_default_credential_signs_in_whatever_the_environment(
    rebuilt: Callable[[Mapping[str, str]], TestClient],
    label: str,
    environment: Mapping[str, str],
    username: str,
    password: str,
) -> None:
    client = rebuilt(environment)

    response = client.post(f"{API}/auth/login", json={"username": username, "password": password})

    assert response.status_code in (401, 422)
    assert "access_token" not in response.text


@pytest.mark.parametrize(("label", "environment"), SETTINGS, ids=[label for label, _ in SETTINGS])
def test_the_real_sign_in_still_works_in_the_same_environment(
    rebuilt: Callable[[Mapping[str, str]], TestClient],
    credentials: Mapping[str, str],
    label: str,
    environment: Mapping[str, str],
) -> None:
    client = rebuilt(environment)

    response = client.post(
        f"{API}/auth/login", json={"username": "asha", "password": credentials["asha"]}
    )

    assert response.status_code == 200
