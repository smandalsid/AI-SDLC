"""Shared helpers of the latency tests (not a test module)."""

import math
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from app.core.passwords import Argon2Hasher
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

THRESHOLDS = Path(__file__).resolve().parents[3] / ".harness" / "config" / "thresholds.env"
BUS_COUNT = 17
SEATS_PER_BUS = 60
STORED_BOOKINGS = 1_000
WARM_UP_CALLS = 5
MEASURED_CALLS = 50
SEATS_PER_WRITE = 6
# Leaves enough free seats for the warm-up and measured writes while the table ends near 1,000 rows.
SEEDED_BEFORE_WRITES = 670
FIRST_WRITE_BUS = SEEDED_BEFORE_WRITES // SEATS_PER_BUS + 1
FIRST_FREE_SEAT = SEEDED_BEFORE_WRITES % SEATS_PER_BUS + 1


def threshold(name: str) -> float:
    for line in THRESHOLDS.read_text().splitlines():
        key, _, value = line.partition("=")
        if key == name:
            return float(value)
    raise KeyError(name)


def p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def within_limit(measure: Callable[[], list[float]], limit_ms: float) -> float:
    """One re-run on a miss; the second measurement decides."""
    observed = p95(measure())
    if observed > limit_ms:
        observed = p95(measure())
    return observed


def stored_bookings(factory: sessionmaker[Session], count: int) -> None:
    """Seed the 17 buses of 60 seats and `count` bookings filled bus by bus."""
    insert_bus = text("INSERT INTO buses (id, name, total_seats) VALUES (:id, :name, :seats)")
    insert_booking = text(
        "INSERT INTO bookings (bus_id, user_id, seat_number, booked_at) "
        "VALUES (:bus_id, :user_id, :seat, SYSUTCDATETIME())"
    )
    extra_buses = [
        {"id": bus, "name": f"Bus {bus}", "seats": SEATS_PER_BUS} for bus in range(4, BUS_COUNT + 1)
    ]
    rows = [
        {"bus_id": n // SEATS_PER_BUS + 1, "user_id": n % 3 + 1, "seat": n % SEATS_PER_BUS + 1}
        for n in range(count)
    ]
    with factory() as session:
        session.execute(text("UPDATE buses SET total_seats = :seats"), {"seats": SEATS_PER_BUS})
        session.execute(text("SET IDENTITY_INSERT buses ON"))
        session.execute(insert_bus, extra_buses)
        session.execute(text("SET IDENTITY_INSERT buses OFF"))
        session.execute(insert_booking, rows)
        session.commit()


def timed_ms(call: Callable[[], int], expected_status: int) -> float:
    started = time.perf_counter()
    status = call()
    elapsed = (time.perf_counter() - started) * 1000
    assert status == expected_status
    return elapsed


def use_production_hashes(
    factory: sessionmaker[Session], credentials: Mapping[str, str]
) -> Argon2Hasher:
    """Stores production-cost hashes of the test passwords, so sign-in costs what it really does."""
    hasher = Argon2Hasher()
    with factory() as session:
        for username, password in credentials.items():
            session.execute(
                text("UPDATE users SET password_hash = :hash WHERE username = :username"),
                {"hash": hasher.hash(password), "username": username},
            )
        session.commit()
    return hasher


def write_plan() -> list[tuple[int, list[int]]]:
    plan: list[tuple[int, list[int]]] = []
    for bus in range(FIRST_WRITE_BUS, BUS_COUNT + 1):
        first = FIRST_FREE_SEAT if bus == FIRST_WRITE_BUS else 1
        for start in range(first, SEATS_PER_BUS - SEATS_PER_WRITE + 2, SEATS_PER_WRITE):
            plan.append((bus, list(range(start, start + SEATS_PER_WRITE))))
    return plan
