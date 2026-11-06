from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta

import pytest
from app.repositories.protocols import FailureWindow
from app.repositories.sign_in_attempt_repository import (
    SignInAttemptRepository,
    failures_statement,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

LOGIN = "/api/v1/auth/login"
NOW = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
FIVE_MINUTES_AGO = NOW - timedelta(minutes=5)
WRONG = "wrong-password"


def ago(**delta: float) -> datetime:
    return NOW - timedelta(**delta)


def store(factory: sessionmaker[Session], rows: list[tuple[str, str, datetime]]) -> None:
    with factory() as session:
        repository = SignInAttemptRepository(session)
        for username, outcome, at in rows:
            repository.record(username, outcome, at)
        session.commit()


def window(factory: sessionmaker[Session], username: str, since: datetime) -> FailureWindow:
    with factory() as session:
        return SignInAttemptRepository(session).failures_since(username, since)


def test_only_failure_rows_newer_than_the_window_count(
    session_factory: sessionmaker[Session],
) -> None:
    store(
        session_factory,
        [
            ("asha", "failure", ago(minutes=6)),
            ("asha", "failure", ago(minutes=4)),
            ("asha", "failure", ago(minutes=1)),
            ("asha", "throttled", ago(seconds=30)),
            ("asha", "signout", ago(seconds=20)),
            ("ravi", "failure", ago(seconds=10)),
        ],
    )

    assert window(session_factory, "asha", FIVE_MINUTES_AGO) == FailureWindow(2, ago(minutes=1))


def test_a_row_exactly_at_the_start_of_the_window_does_not_count(
    session_factory: sessionmaker[Session],
) -> None:
    store(session_factory, [("asha", "failure", FIVE_MINUTES_AGO)])

    assert window(session_factory, "asha", FIVE_MINUTES_AGO) == FailureWindow(0, None)


def test_only_failures_after_the_latest_success_of_the_same_username_count(
    session_factory: sessionmaker[Session],
) -> None:
    store(
        session_factory,
        [
            ("asha", "failure", ago(minutes=4)),
            ("asha", "failure", ago(minutes=3, seconds=30)),
            ("asha", "success", ago(minutes=3)),
            ("asha", "failure", ago(minutes=2)),
            ("ravi", "success", ago(seconds=5)),
        ],
    )

    assert window(session_factory, "asha", FIVE_MINUTES_AGO) == FailureWindow(1, ago(minutes=2))


def test_an_empty_history_gives_a_zero_count(session_factory: sessionmaker[Session]) -> None:
    assert window(session_factory, "asha", FIVE_MINUTES_AGO) == FailureWindow(0, None)


@pytest.mark.parametrize("asked", ["ASHA", "asha ", "Asha"])
def test_case_and_trailing_space_variants_share_the_count_of_the_username(
    session_factory: sessionmaker[Session], asked: str
) -> None:
    store(
        session_factory,
        [("asha", "failure", ago(minutes=2)), ("ASHA ", "failure", ago(minutes=1))],
    )

    assert window(session_factory, asked, FIVE_MINUTES_AGO) == FailureWindow(2, ago(minutes=1))


def test_variants_typed_by_a_guesser_block_the_real_username_but_never_sign_in(
    client: TestClient, credentials: Mapping[str, str]
) -> None:
    exact_name_needed = client.post(
        LOGIN, json={"username": "ASHA", "password": credentials["asha"]}
    )
    assert exact_name_needed.status_code == 401

    for name in ["ASHA", "asha ", "Asha", "aSHA"]:
        assert client.post(LOGIN, json={"username": name, "password": WRONG}).status_code == 401

    blocked = client.post(LOGIN, json={"username": "asha", "password": credentials["asha"]})
    assert blocked.status_code == 429


def test_the_count_lives_in_the_database_so_two_app_instances_share_it(
    make_app: Callable[[], FastAPI], credentials: Mapping[str, str]
) -> None:
    first = TestClient(make_app())
    second = TestClient(make_app())

    for client, times in [(first, 3), (second, 2)]:
        for _ in range(times):
            response = client.post(LOGIN, json={"username": "asha", "password": WRONG})
            assert response.status_code == 401

    for client in (first, second):
        response = client.post(LOGIN, json={"username": "asha", "password": credentials["asha"]})
        assert response.status_code == 429


def test_the_count_query_uses_the_username_and_time_index(
    engine: Engine, session_factory: sessionmaker[Session]
) -> None:
    names = [f"user{index % 200}" for index in range(4000)]
    store(
        session_factory, [(name, "failure", ago(seconds=index)) for index, name in enumerate(names)]
    )
    statement = failures_statement("user7", FIVE_MINUTES_AGO)
    sql = str(statement.compile(dialect=engine.dialect, compile_kwargs={"literal_binds": True}))

    with engine.connect() as connection:
        connection.exec_driver_sql("SET SHOWPLAN_XML ON")
        plan = str(connection.exec_driver_sql(sql).scalar_one())
        connection.exec_driver_sql("SET SHOWPLAN_XML OFF")

    assert "ix_sign_in_attempts_username_attempted_at" in plan
