from collections.abc import Mapping
from datetime import timedelta

from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from ..conftest import FakeClock

LOGIN = "/api/v1/auth/login"
WRONG = "wrong-password"


def post(client: TestClient, username: str, password: str) -> Response:
    return client.post(LOGIN, json={"username": username, "password": password})


def fail(client: TestClient, username: str, times: int = 5) -> None:
    for _ in range(times):
        assert post(client, username, WRONG).status_code == 401


def count(factory: sessionmaker[Session], table: str) -> int:
    with factory() as session:
        return int(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())  # noqa: S608


def wait_named_in(response: Response) -> int:
    message = str(response.json()["error"]["message"])
    assert message.startswith("Too many failed sign-in attempts. Try again in ")
    return int(message.split(" in ")[1].split(" ")[0])


def test_five_wrong_passwords_then_the_right_one_is_refused_with_429_and_a_retry_after(
    client: TestClient, session_factory: sessionmaker[Session], credentials: Mapping[str, str]
) -> None:
    fail(client, "asha")

    response = post(client, "asha", credentials["asha"])

    assert response.status_code == 429
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "too_many_attempts"
    assert response.headers["retry-after"] == str(wait_named_in(response)) == "60"
    assert "access_token" not in response.text
    assert count(session_factory, "sessions") == 0


def test_the_refused_attempt_is_recorded_as_throttled(
    client: TestClient, session_factory: sessionmaker[Session], credentials: Mapping[str, str]
) -> None:
    fail(client, "asha")
    post(client, "asha", credentials["asha"])

    with session_factory() as session:
        rows = session.execute(
            text("SELECT outcome FROM sign_in_attempts WHERE username = 'asha' ORDER BY id")
        ).all()
    assert [row[0] for row in rows] == ["failure"] * 5 + ["throttled"]


def test_another_user_still_signs_in_meanwhile(
    client: TestClient, credentials: Mapping[str, str]
) -> None:
    fail(client, "asha")

    assert post(client, "ravi", credentials["ravi"]).status_code == 200


def test_the_wait_shrinks_with_the_clock_and_asha_signs_in_after_60_seconds(
    client: TestClient, fake_clock: FakeClock, credentials: Mapping[str, str]
) -> None:
    fail(client, "asha")
    fake_clock.current += timedelta(seconds=25)

    midway = post(client, "asha", credentials["asha"])
    assert midway.status_code == 429
    assert midway.headers["retry-after"] == str(wait_named_in(midway)) == "35"

    fake_clock.current += timedelta(seconds=35)
    assert post(client, "asha", credentials["asha"]).status_code == 200


def test_throttled_attempts_do_not_extend_the_wait(
    client: TestClient, fake_clock: FakeClock, credentials: Mapping[str, str]
) -> None:
    fail(client, "asha")
    for _ in range(3):
        fake_clock.current += timedelta(seconds=15)
        assert post(client, "asha", credentials["asha"]).status_code == 429

    fake_clock.current += timedelta(seconds=15)

    assert post(client, "asha", credentials["asha"]).status_code == 200


def test_five_failures_for_an_unknown_username_give_the_same_429_shape(
    client: TestClient, credentials: Mapping[str, str]
) -> None:
    fail(client, "asha")
    fail(client, "nobody")

    known = post(client, "asha", credentials["asha"])
    unknown = post(client, "nobody", WRONG)

    assert unknown.status_code == known.status_code == 429
    assert unknown.json() == known.json()
    assert unknown.headers["retry-after"] == known.headers["retry-after"]


def test_a_success_resets_the_count(client: TestClient, credentials: Mapping[str, str]) -> None:
    fail(client, "asha", 4)
    assert post(client, "asha", credentials["asha"]).status_code == 200

    fail(client, "asha", 4)

    assert post(client, "asha", credentials["asha"]).status_code == 200
