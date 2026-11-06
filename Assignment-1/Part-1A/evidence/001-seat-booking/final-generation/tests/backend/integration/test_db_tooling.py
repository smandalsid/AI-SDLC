from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from app.core.config import Settings
from app.db import admin, seed, session
from app.db.admin import (
    create_database_if_missing,
    drop_and_create_database,
    master_engine,
    probe_master,
)
from app.db.admin import main as admin_main
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

NEW_USER = "INSERT INTO users (name) VALUES ('Zed')"


def user_names(factory: sessionmaker[Session]) -> list[str]:
    with factory() as reader:
        rows = reader.execute(text("SELECT name FROM users ORDER BY id")).all()
    return [str(row[0]) for row in rows]


def test_unit_of_work_commits_when_the_block_succeeds(
    session_factory: sessionmaker[Session],
) -> None:
    with session.unit_of_work(session_factory) as work:
        work.execute(text(NEW_USER))

    assert "Zed" in user_names(session_factory)


def test_unit_of_work_rolls_back_and_reraises_when_the_block_fails(
    session_factory: sessionmaker[Session],
) -> None:
    before = user_names(session_factory)

    with pytest.raises(RuntimeError, match="boom"):
        with session.unit_of_work(session_factory) as work:
            work.execute(text(NEW_USER))
            raise RuntimeError("boom")

    assert user_names(session_factory) == before


def test_get_session_commits_when_the_request_finishes(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(session, "get_session_factory", lambda: session_factory)

    with contextmanager(session.get_session)() as work:
        work.execute(text(NEW_USER))

    assert "Zed" in user_names(session_factory)


def test_get_session_rolls_back_when_the_request_fails(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(session, "get_session_factory", lambda: session_factory)
    before = user_names(session_factory)

    with pytest.raises(RuntimeError, match="boom"):
        with contextmanager(session.get_session)() as work:
            work.execute(text(NEW_USER))
            raise RuntimeError("boom")

    assert user_names(session_factory) == before


def test_seed_main_reseeds_the_given_database_and_prints_only_counts(
    settings: Settings,
    test_database: str,
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(seed, "get_settings", lambda: settings)
    with session_factory() as work:
        work.execute(text(NEW_USER))
        work.commit()

    exit_code = seed.main(["--database", test_database])

    output = capsys.readouterr()
    assert exit_code == 0
    assert output.out.strip() == "seeded 3 buses, 3 users, 0 bookings"
    assert user_names(session_factory) == ["Asha", "Ravi", "Meera"]
    secret = settings.db_password.get_secret_value()
    assert secret not in output.out and secret not in output.err


def test_probe_master_succeeds(settings: Settings) -> None:
    probe_master(settings)


def database_exists(settings: Settings, name: str) -> bool:
    engine = master_engine(settings)
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT 1 FROM sys.databases WHERE name = :name"), {"name": name}
            ).first()
    finally:
        engine.dispose()
    return row is not None


def scratch_has_marker_table(settings: Settings, name: str) -> bool:
    engine = create_engine(settings.database_url(name))
    try:
        with engine.connect() as connection:
            row = connection.execute(text("SELECT 1 FROM sys.tables WHERE name = 'marker'")).first()
    finally:
        engine.dispose()
    return row is not None


def add_marker_table(settings: Settings, name: str) -> None:
    engine = create_engine(settings.database_url(name))
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE marker (id INT)"))
    finally:
        engine.dispose()


@pytest.fixture
def scratch_database(settings: Settings) -> Iterator[str]:
    name = f"{settings.db_name}_toolingscratch_test"
    drop_scratch(settings, name)
    yield name
    drop_scratch(settings, name)


def drop_scratch(settings: Settings, name: str) -> None:
    assert name.endswith("_toolingscratch_test")
    engine = master_engine(settings)
    quoted = engine.dialect.identifier_preparer.quote(name)
    try:
        with engine.connect() as connection:
            if database_exists(settings, name):
                connection.execute(
                    text(f"ALTER DATABASE {quoted} SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
                )
                connection.execute(text(f"DROP DATABASE {quoted}"))
    finally:
        engine.dispose()


def test_create_database_if_missing_creates_once_and_is_idempotent(
    settings: Settings, scratch_database: str
) -> None:
    assert not database_exists(settings, scratch_database)

    create_database_if_missing(settings, scratch_database)
    add_marker_table(settings, scratch_database)
    create_database_if_missing(settings, scratch_database)

    assert database_exists(settings, scratch_database)
    assert scratch_has_marker_table(settings, scratch_database)


def test_drop_and_create_database_recreates_an_empty_database(
    settings: Settings, scratch_database: str
) -> None:
    create_database_if_missing(settings, scratch_database)
    add_marker_table(settings, scratch_database)

    drop_and_create_database(settings, scratch_database)

    assert database_exists(settings, scratch_database)
    assert not scratch_has_marker_table(settings, scratch_database)


@pytest.fixture
def admin_settings(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin, "get_settings", lambda: settings)


@pytest.mark.usefixtures("admin_settings")
def test_admin_main_wait_returns_success_when_the_server_answers() -> None:
    assert admin_main(["wait"]) == 0


@pytest.mark.usefixtures("admin_settings")
def test_admin_main_create_makes_the_named_database(
    settings: Settings, scratch_database: str
) -> None:
    assert admin_main(["create", "--database", scratch_database]) == 0

    assert database_exists(settings, scratch_database)


@pytest.mark.usefixtures("admin_settings")
def test_admin_main_recreate_empties_the_named_database(
    settings: Settings, scratch_database: str
) -> None:
    create_database_if_missing(settings, scratch_database)
    add_marker_table(settings, scratch_database)

    assert admin_main(["recreate", "--database", scratch_database]) == 0

    assert database_exists(settings, scratch_database)
    assert not scratch_has_marker_table(settings, scratch_database)


def test_admin_main_rejects_an_unknown_command() -> None:
    with pytest.raises(SystemExit) as raised:
        admin_main(["drop"])

    assert raised.value.code == 2
