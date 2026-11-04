from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import Settings
from app.core.passwords import Argon2Hasher
from app.db.admin import drop_and_create_database, master_engine, validated_name
from sqlalchemy import Engine, create_engine, inspect, text

ALEMBIC_INI = Path(__file__).resolve().parents[3] / "src" / "backend" / "alembic.ini"
LEGACY_USERS = ["Asha", "Ravi", "Meera"]
NEW_CONSTRAINTS = {
    "uq_users_username",
    "ck_users_username_not_blank",
    "ck_users_password_hash_not_blank",
}


def drop_database(settings: Settings, name: str) -> None:
    validated_name(name)
    assert name.endswith("_test")
    engine = master_engine(settings)
    quoted = engine.dialect.identifier_preparer.quote(name)
    with engine.connect() as connection:
        connection.execute(text(f"ALTER DATABASE {quoted} SET SINGLE_USER WITH ROLLBACK IMMEDIATE"))
        connection.execute(text(f"DROP DATABASE {quoted}"))
    engine.dispose()


@pytest.fixture
def scratch_engine(settings: Settings) -> Iterator[tuple[Engine, Config]]:
    name = f"{settings.db_name}_mig0002_test"
    drop_and_create_database(settings, name)
    config = Config(str(ALEMBIC_INI))
    config.attributes["database"] = name
    engine = create_engine(settings.database_url(name))
    try:
        yield engine, config
    finally:
        engine.dispose()
        drop_database(settings, name)


def seed_legacy_rows(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO buses (name, total_seats) VALUES ('Bus A', 20)"))
        for name in LEGACY_USERS:
            connection.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": name})
        connection.execute(
            text(
                "INSERT INTO bookings (bus_id, user_id, seat_number, booked_at) "
                "VALUES (1, 1, 3, SYSUTCDATETIME())"
            )
        )


def user_columns(engine: Engine) -> set[str]:
    return {str(column["name"]) for column in inspect(engine).get_columns("users")}


def constraint_names(engine: Engine) -> set[str]:
    query = (
        "SELECT name FROM sys.check_constraints WHERE parent_object_id = OBJECT_ID('users') "
        "UNION SELECT name FROM sys.key_constraints WHERE parent_object_id = OBJECT_ID('users')"
    )
    with engine.connect() as connection:
        return {str(row[0]) for row in connection.execute(text(query)).all()}


def test_upgrade_backfills_existing_users_and_locks_them_out(
    scratch_engine: tuple[Engine, Config],
) -> None:
    engine, config = scratch_engine
    command.upgrade(config, "0001")
    seed_legacy_rows(engine)

    command.upgrade(config, "0002")

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT name, username, password_hash FROM users ORDER BY id")
        ).all()
        booking = connection.execute(
            text("SELECT bus_id, user_id, seat_number FROM bookings")
        ).all()
    assert [(row[0], row[1]) for row in rows] == [(name, name.lower()) for name in LEGACY_USERS]
    assert {str(row[2]) for row in rows} == {"!"}
    assert [tuple(row) for row in booking] == [(1, 1, 3)]
    assert NEW_CONSTRAINTS <= constraint_names(engine)
    assert {"sessions", "sign_in_attempts"} <= set(inspect(engine).get_table_names())
    assert Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1).verify("!", "anything") is False


def test_downgrade_removes_the_new_columns_and_tables_and_keeps_the_old_data(
    scratch_engine: tuple[Engine, Config],
) -> None:
    engine, config = scratch_engine
    command.upgrade(config, "0001")
    seed_legacy_rows(engine)
    command.upgrade(config, "0002")

    command.downgrade(config, "0001")

    assert user_columns(engine) == {"id", "name"}
    assert not {"sessions", "sign_in_attempts"} & set(inspect(engine).get_table_names())
    assert not NEW_CONSTRAINTS & constraint_names(engine)
    with engine.connect() as connection:
        names = [
            str(row[0])
            for row in connection.execute(text("SELECT name FROM users ORDER BY id")).all()
        ]
        bookings = connection.execute(text("SELECT COUNT(*) FROM bookings")).scalar_one()
    assert names == LEGACY_USERS
    assert bookings == 1
