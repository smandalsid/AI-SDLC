"""The injectable clock and the request-scoped in-memory reminder store."""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.clock import SystemClock
from app.services.store import InMemoryReminderStore, Reminder

pytestmark = pytest.mark.covers("FR-6", "FR-7")

T1 = datetime(2026, 11, 6, 10, 0, tzinfo=UTC)


def test_system_clock_is_timezone_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None and now.utcoffset() == timedelta(0)
    assert abs(now - datetime.now(UTC)) < timedelta(seconds=5)


def test_store_lists_adds_updates_and_removes() -> None:
    store = InMemoryReminderStore([Reminder("r1", "Dentist", T1)])
    new_id = store.add("Gym", T1)
    assert new_id != "r1" and [r.id for r in store.list()] == ["r1", new_id]
    store.set_time("r1", T1 + timedelta(hours=1))
    assert store.list()[0].time == T1 + timedelta(hours=1) and store.list()[0].title == "Dentist"
    store.remove(new_id)
    assert [r.id for r in store.list()] == ["r1"]


def test_minted_ids_never_collide_with_existing_ids() -> None:
    store = InMemoryReminderStore([Reminder("rem-1", "A", T1), Reminder("rem-2", "B", T1)])
    assert store.add("C", T1) not in {"rem-1", "rem-2"}


def test_unknown_id_is_a_programming_error() -> None:
    store = InMemoryReminderStore()
    with pytest.raises(KeyError):
        store.remove("zz")
    with pytest.raises(KeyError):
        store.set_time("zz", T1)


def test_stores_are_isolated_and_listing_returns_a_copy() -> None:
    first, second = InMemoryReminderStore(), InMemoryReminderStore()
    first.add("A", T1)
    assert second.list() == []
    snapshot = first.list()
    first.add("B", T1)
    assert len(snapshot) == 1
