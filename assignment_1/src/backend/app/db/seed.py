import argparse
import sys
from collections.abc import Mapping, Sequence

from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.passwords import Argon2Hasher, PasswordHasher

BUSES: list[dict[str, int | str]] = [
    {"id": 1, "name": "Bus A", "total_seats": 20},
    {"id": 2, "name": "Bus B", "total_seats": 30},
    {"id": 3, "name": "Bus C", "total_seats": 40},
]
USERS: list[dict[str, int | str]] = [
    {"id": 1, "name": "Asha", "username": "asha"},
    {"id": 2, "name": "Ravi", "username": "ravi"},
    {"id": 3, "name": "Meera", "username": "meera"},
]


class MissingMockPasswordError(ValueError):
    """A seeded user has no mock password configured; the message names usernames only."""


def password_hashes_from_settings(
    passwords: Mapping[str, SecretStr], usernames: Sequence[str], hasher: PasswordHasher
) -> dict[str, str]:
    missing = [username for username in usernames if username not in passwords]
    if missing:
        raise MissingMockPasswordError(
            f"no mock password configured for: {', '.join(missing)} "
            "(set MOCK_USER_PASSWORDS in .env)"
        )
    return {name: hasher.hash(passwords[name].get_secret_value()) for name in usernames}


def reset_data(session: Session, password_hashes: Mapping[str, str]) -> None:
    """Reset the tables to the documented mock data; repeatable, and ends every session."""
    # TRUNCATE also restarts the booking identity so new ids begin at 1.
    session.execute(text("TRUNCATE TABLE bookings"))
    session.execute(text("TRUNCATE TABLE sessions"))
    session.execute(text("TRUNCATE TABLE sign_in_attempts"))
    session.execute(text("DELETE FROM users"))
    session.execute(text("DELETE FROM buses"))

    session.execute(text("SET IDENTITY_INSERT buses ON"))
    session.execute(
        text("INSERT INTO buses (id, name, total_seats) VALUES (:id, :name, :total_seats)"), BUSES
    )
    session.execute(text("SET IDENTITY_INSERT buses OFF"))

    users = [{**user, "password_hash": password_hashes[str(user["username"])]} for user in USERS]
    session.execute(text("SET IDENTITY_INSERT users ON"))
    session.execute(
        text(
            "INSERT INTO users (id, name, username, password_hash) "
            "VALUES (:id, :name, :username, :password_hash)"
        ),
        users,
    )
    session.execute(text("SET IDENTITY_INSERT users OFF"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reset the database to the mock data")
    parser.add_argument("--database", help="defaults to DB_NAME")
    args = parser.parse_args(argv)
    settings = get_settings()

    usernames = [str(user["username"]) for user in USERS]
    try:
        hashes = password_hashes_from_settings(
            settings.mock_user_passwords, usernames, Argon2Hasher()
        )
    except MissingMockPasswordError as error:
        print(f"cannot seed: {error}", file=sys.stderr)
        return 2

    engine = create_engine(settings.database_url(args.database or settings.db_name))
    with sessionmaker(engine)() as session:
        reset_data(session, hashes)
        session.commit()
    engine.dispose()
    print(f"seeded {len(BUSES)} buses, {len(USERS)} users, 0 bookings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
