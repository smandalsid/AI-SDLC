import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.seed import reset_data

SEEDED_BUSES = [(1, "Bus A", 20), (2, "Bus B", 30), (3, "Bus C", 40)]
SEEDED_USERS = [(1, "Asha"), (2, "Ravi"), (3, "Meera")]

INSERT_BOOKING = (
    "INSERT INTO bookings (bus_id, user_id, seat_number, booked_at) "
    "OUTPUT INSERTED.id VALUES (:bus_id, :user_id, :seat, SYSUTCDATETIME())"
)


def snapshot(session: Session) -> tuple[list[tuple[int, str, int]], list[tuple[int, str]]]:
    bus_rows = session.execute(text("SELECT id, name, total_seats FROM buses ORDER BY id"))
    user_rows = session.execute(text("SELECT id, name FROM users ORDER BY id"))
    buses = [(int(row[0]), str(row[1]), int(row[2])) for row in bus_rows]
    users = [(int(row[0]), str(row[1])) for row in user_rows]
    return buses, users


def insert_booking(session: Session, bus_id: int, user_id: int, seat: int) -> int:
    row = session.execute(
        text(INSERT_BOOKING), {"bus_id": bus_id, "user_id": user_id, "seat": seat}
    )
    return int(row.scalar_one())


def booking_count(session: Session) -> int:
    return int(session.execute(text("SELECT COUNT(*) FROM bookings")).scalar_one())


def test_schema_has_exactly_the_application_tables(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())

    assert tables == {"buses", "users", "bookings", "alembic_version"}


def test_seed_yields_the_documented_mock_data(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        assert snapshot(session) == (SEEDED_BUSES, SEEDED_USERS)
        assert booking_count(session) == 0


def test_a_second_booking_for_the_same_bus_and_seat_is_rejected(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        insert_booking(session, bus_id=1, user_id=1, seat=3)
        with pytest.raises(IntegrityError):
            insert_booking(session, bus_id=1, user_id=2, seat=3)


def test_same_seat_on_another_bus_is_allowed(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        insert_booking(session, bus_id=1, user_id=1, seat=3)
        insert_booking(session, bus_id=2, user_id=1, seat=3)
        assert booking_count(session) == 2


@pytest.mark.parametrize("total_seats", [0, 61])
def test_total_seats_outside_1_to_60_is_rejected(
    session_factory: sessionmaker[Session], total_seats: int
) -> None:
    with session_factory() as session, pytest.raises(IntegrityError):
        session.execute(
            text("INSERT INTO buses (name, total_seats) VALUES ('Bus Z', :seats)"),
            {"seats": total_seats},
        )


def test_seat_number_below_1_is_rejected(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session, pytest.raises(IntegrityError):
        insert_booking(session, bus_id=1, user_id=1, seat=0)


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO buses (name, total_seats) VALUES ('Bus A', 10)",
        "INSERT INTO users (name) VALUES ('Asha')",
        "INSERT INTO buses (name, total_seats) VALUES ('   ', 10)",
        "INSERT INTO users (name) VALUES ('   ')",
    ],
)
def test_duplicate_and_blank_names_are_rejected(
    session_factory: sessionmaker[Session], statement: str
) -> None:
    with session_factory() as session, pytest.raises(IntegrityError):
        session.execute(text(statement))


def test_seed_is_idempotent_and_resets_bookings(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        insert_booking(session, bus_id=1, user_id=1, seat=3)
        insert_booking(session, bus_id=1, user_id=2, seat=4)
        session.commit()

        reset_data(session)
        session.commit()
        reset_data(session)
        session.commit()

        assert snapshot(session) == (SEEDED_BUSES, SEEDED_USERS)
        assert booking_count(session) == 0
        assert insert_booking(session, bus_id=1, user_id=1, seat=1) == 1
