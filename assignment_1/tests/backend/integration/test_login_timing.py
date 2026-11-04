from collections.abc import Mapping
from datetime import timedelta

import pytest
from app.api.deps import get_password_verifier
from app.core.passwords import PasswordVerifier
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.orm import Session, sessionmaker

from ..conftest import FakeClock
from .perf_support import p95, timed_ms, use_production_hashes

pytestmark = pytest.mark.perf

LOGIN = "/api/v1/auth/login"
ATTEMPTS = 1_000
MAX_P95_DIFFERENCE_MS = 50.0
KNOWN = ("asha", "ravi", "meera")
# Longer than the 5-minute failure window, so the throttle never interferes.
STEP = timedelta(minutes=6)


def test_unknown_usernames_and_wrong_passwords_look_and_take_the_same(
    app: FastAPI,
    client: TestClient,
    fake_clock: FakeClock,
    session_factory: sessionmaker[Session],
    credentials: Mapping[str, str],
) -> None:
    hasher = use_production_hashes(session_factory, credentials)

    def production_verifier() -> PasswordVerifier:
        return hasher

    app.dependency_overrides[get_password_verifier] = production_verifier
    unknown_ms: list[float] = []
    wrong_ms: list[float] = []
    shapes: set[tuple[int, str, str, tuple[str, ...]]] = set()

    def attempt(username: str, into: list[float]) -> None:
        responses: list[Response] = []

        def send() -> int:
            responses.append(client.post(LOGIN, json={"username": username, "password": "wrong"}))
            return responses[0].status_code

        into.append(timed_ms(send, 401))
        body = responses[0].json()
        error = body["error"]
        shapes.add((responses[0].status_code, error["code"], error["message"], tuple(body)))
        fake_clock.current += STEP

    for index in range(ATTEMPTS):
        if index % 2:
            attempt(f"nobody{index}", unknown_ms)
        else:
            attempt(KNOWN[index % len(KNOWN)], wrong_ms)

    assert len(shapes) == 1
    difference = abs(p95(unknown_ms) - p95(wrong_ms))
    assert difference <= MAX_P95_DIFFERENCE_MS, f"p95 differs by {difference:.1f} ms"
