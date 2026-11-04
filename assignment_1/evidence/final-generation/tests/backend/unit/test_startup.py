from functools import partial

import pytest
from app.core.errors import DatabaseUnavailableError
from app.db.session import get_session, wait_for_database
from app.main import create_app
from fastapi.testclient import TestClient


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FlakyProbe:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("database not ready")


class FakeSession:
    def execute(self, statement: object) -> None:
        return None


def always_down() -> None:
    raise DatabaseUnavailableError("database never answered")


def test_wait_for_database_retries_until_the_probe_succeeds() -> None:
    clock, probe = FakeClock(), FlakyProbe(failures=2)

    wait_for_database(
        probe,
        timeout_seconds=10,
        interval_seconds=1,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    assert probe.calls == 3
    assert clock.sleeps == [1, 1]


def test_wait_for_database_gives_up_after_the_timeout() -> None:
    clock, probe = FakeClock(), FlakyProbe(failures=1_000_000)

    with pytest.raises(DatabaseUnavailableError):
        wait_for_database(
            probe,
            timeout_seconds=5,
            interval_seconds=1,
            sleep=clock.sleep,
            monotonic=clock.monotonic,
        )

    assert 5 <= probe.calls <= 7
    assert sum(clock.sleeps) >= 5


def test_app_serves_requests_once_the_database_answers_after_retries() -> None:
    clock, probe = FakeClock(), FlakyProbe(failures=2)
    wait = partial(
        wait_for_database,
        probe,
        timeout_seconds=60,
        interval_seconds=1,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )
    app = create_app(wait_for_db=wait)
    app.dependency_overrides[get_session] = lambda: FakeSession()

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert probe.calls == 3


def test_app_refuses_to_start_when_the_database_never_answers() -> None:
    app = create_app(wait_for_db=always_down)

    with pytest.raises(DatabaseUnavailableError), TestClient(app):
        pass
