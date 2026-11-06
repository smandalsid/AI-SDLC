from collections.abc import Mapping

import pytest
from app.core.passwords import Argon2Hasher
from app.db.seed import reset_data
from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine.interfaces import ReflectedColumn
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

INSERT_USER = (
    "INSERT INTO users (name, username, password_hash) VALUES (:name, :username, :password_hash)"
)
INSERT_SESSION = (
    "INSERT INTO sessions (id, user_id, started_at, expires_at) "
    "VALUES (:id, :user_id, SYSUTCDATETIME(), DATEADD(minute, :minutes, SYSUTCDATETIME()))"
)
INSERT_ATTEMPT = (
    "INSERT INTO sign_in_attempts (username, outcome, attempted_at) "
    "VALUES (:username, :outcome, SYSUTCDATETIME())"
)
SESSION_ID = "0123456789abcdef0123456789abcdef"
SEEDED = [(1, "Asha", "asha"), (2, "Ravi", "ravi"), (3, "Meera", "meera")]


def count(session: Session, table: str) -> int:
    return int(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())  # noqa: S608


def add_user(session: Session, name: str, username: str, stored_hash: str) -> None:
    session.execute(
        text(INSERT_USER), {"name": name, "username": username, "password_hash": stored_hash}
    )


def seeded_users(session: Session) -> list[tuple[int, str, str]]:
    rows = session.execute(text("SELECT id, name, username FROM users ORDER BY id")).all()
    return [(int(row[0]), str(row[1]), str(row[2])) for row in rows]


def column_info(engine: Engine, table: str, column: str) -> ReflectedColumn:
    return next(item for item in inspect(engine).get_columns(table) if item["name"] == column)


def test_schema_has_the_five_application_tables(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())

    assert tables == {
        "buses",
        "users",
        "bookings",
        "sessions",
        "sign_in_attempts",
        "alembic_version",
    }


@pytest.mark.parametrize(("column", "length"), [("username", 50), ("password_hash", 255)])
def test_user_credential_columns_have_the_documented_size_and_are_not_null(
    engine: Engine, column: str, length: int
) -> None:
    info = column_info(engine, "users", column)

    assert info["nullable"] is False
    assert getattr(info["type"], "length", None) == length


@pytest.mark.parametrize(
    ("name", "username", "stored_hash"),
    [
        ("Dup One", "asha", "x"),
        ("Dup Two", "ASHA", "x"),
        ("Blank User", "   ", "x"),
        ("Empty Hash", "newbie", ""),
    ],
)
def test_user_credentials_constraints_reject_bad_rows(
    session_factory: sessionmaker[Session], name: str, username: str, stored_hash: str
) -> None:
    with session_factory() as session, pytest.raises(IntegrityError):
        add_user(session, name, username, stored_hash)


def test_a_user_without_a_username_or_hash_is_rejected(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session, pytest.raises(IntegrityError):
        session.execute(text("INSERT INTO users (name) VALUES ('No Credentials')"))


def test_sessions_table_shape(engine: Engine) -> None:
    id_column = column_info(engine, "sessions", "id")

    assert getattr(id_column["type"], "length", None) == 32
    assert inspect(engine).get_pk_constraint("sessions")["constrained_columns"] == ["id"]
    assert column_info(engine, "sessions", "ended_at")["nullable"] is True
    for name in ("user_id", "started_at", "expires_at"):
        assert column_info(engine, "sessions", name)["nullable"] is False
    foreign_keys = inspect(engine).get_foreign_keys("sessions")
    assert [(fk["constrained_columns"], fk["referred_table"]) for fk in foreign_keys] == [
        (["user_id"], "users")
    ]


def test_a_session_for_a_missing_user_is_rejected(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session, pytest.raises(IntegrityError):
        session.execute(text(INSERT_SESSION), {"id": SESSION_ID, "user_id": 999, "minutes": 30})


@pytest.mark.parametrize("minutes", [0, -5])
def test_a_session_must_expire_after_it_starts(
    session_factory: sessionmaker[Session], minutes: int
) -> None:
    with session_factory() as session, pytest.raises(IntegrityError):
        session.execute(text(INSERT_SESSION), {"id": SESSION_ID, "user_id": 1, "minutes": minutes})


def test_a_valid_session_starts_open(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.execute(text(INSERT_SESSION), {"id": SESSION_ID, "user_id": 1, "minutes": 30})
        ended = session.execute(text("SELECT ended_at FROM sessions")).scalar_one()

    assert ended is None


def test_sign_in_attempts_table_shape(engine: Engine) -> None:
    inspector = inspect(engine)

    assert (
        getattr(column_info(engine, "sign_in_attempts", "username")["type"], "length", None) == 50
    )
    assert getattr(column_info(engine, "sign_in_attempts", "outcome")["type"], "length", None) == 10
    assert inspector.get_foreign_keys("sign_in_attempts") == []
    indexes = {
        index["name"]: index["column_names"] for index in inspector.get_indexes("sign_in_attempts")
    }
    assert indexes["ix_sign_in_attempts_username_attempted_at"] == ["username", "attempted_at"]


@pytest.mark.parametrize("outcome", ["success", "failure", "throttled", "signout"])
def test_every_documented_outcome_is_accepted_even_for_an_unknown_username(
    session_factory: sessionmaker[Session], outcome: str
) -> None:
    with session_factory() as session:
        session.execute(text(INSERT_ATTEMPT), {"username": "nobody", "outcome": outcome})
        assert count(session, "sign_in_attempts") == 1


def test_an_undocumented_outcome_is_rejected(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session, pytest.raises(IntegrityError):
        session.execute(text(INSERT_ATTEMPT), {"username": "asha", "outcome": "bogus"})


def test_seed_creates_the_three_users_with_hashes_that_verify(
    session_factory: sessionmaker[Session],
    credentials: Mapping[str, str],
    password_hasher: Argon2Hasher,
) -> None:
    with session_factory() as session:
        assert seeded_users(session) == SEEDED
        rows = session.execute(text("SELECT username, password_hash FROM users")).all()

    assert len(rows) == 3
    for username, stored in rows:
        assert str(stored).startswith("$argon2id$")
        assert password_hasher.verify(str(stored), credentials[str(username)])
        assert not password_hasher.verify(str(stored), credentials[str(username)] + "x")


def test_reset_empties_bookings_sessions_and_attempts_and_ends_every_session(
    session_factory: sessionmaker[Session], password_hashes: Mapping[str, str]
) -> None:
    with session_factory() as session:
        session.execute(
            text(
                "INSERT INTO bookings (bus_id, user_id, seat_number, booked_at) "
                "VALUES (1, 1, 3, SYSUTCDATETIME())"
            )
        )
        session.execute(text(INSERT_SESSION), {"id": SESSION_ID, "user_id": 1, "minutes": 30})
        session.execute(text(INSERT_ATTEMPT), {"username": "asha", "outcome": "failure"})
        session.commit()

        reset_data(session, password_hashes)
        session.commit()

        assert [
            count(session, table) for table in ("bookings", "sessions", "sign_in_attempts")
        ] == [
            0,
            0,
            0,
        ]


def test_two_consecutive_resets_give_the_same_logical_state(
    session_factory: sessionmaker[Session], password_hashes: Mapping[str, str]
) -> None:
    with session_factory() as session:
        reset_data(session, password_hashes)
        session.commit()
        first = seeded_users(session)
        reset_data(session, password_hashes)
        session.commit()

        assert seeded_users(session) == first == SEEDED
