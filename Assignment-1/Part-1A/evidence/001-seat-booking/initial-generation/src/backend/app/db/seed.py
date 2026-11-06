import argparse
from collections.abc import Sequence
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

BUSES: list[dict[str, Any]] = [
    {"id": 1, "name": "Bus A", "total_seats": 20},
    {"id": 2, "name": "Bus B", "total_seats": 30},
    {"id": 3, "name": "Bus C", "total_seats": 40},
]
USERS: list[dict[str, Any]] = [
    {"id": 1, "name": "Asha"},
    {"id": 2, "name": "Ravi"},
    {"id": 3, "name": "Meera"},
]


def reset_data(session: Session) -> None:
    """Reset the tables to the documented mock data; repeatable."""
    # TRUNCATE also restarts the booking identity so new ids begin at 1.
    session.execute(text("TRUNCATE TABLE bookings"))
    session.execute(text("DELETE FROM users"))
    session.execute(text("DELETE FROM buses"))

    session.execute(text("SET IDENTITY_INSERT buses ON"))
    session.execute(
        text("INSERT INTO buses (id, name, total_seats) VALUES (:id, :name, :total_seats)"), BUSES
    )
    session.execute(text("SET IDENTITY_INSERT buses OFF"))

    session.execute(text("SET IDENTITY_INSERT users ON"))
    session.execute(text("INSERT INTO users (id, name) VALUES (:id, :name)"), USERS)
    session.execute(text("SET IDENTITY_INSERT users OFF"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reset the database to the mock data")
    parser.add_argument("--database", help="defaults to DB_NAME")
    args = parser.parse_args(argv)
    settings = get_settings()

    engine = create_engine(settings.database_url(args.database or settings.db_name))
    with sessionmaker(engine)() as session:
        reset_data(session)
        session.commit()
    engine.dispose()
    print(f"seeded {len(BUSES)} buses, {len(USERS)} users, 0 bookings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
