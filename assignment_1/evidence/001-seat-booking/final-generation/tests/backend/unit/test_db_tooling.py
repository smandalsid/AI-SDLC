from datetime import UTC, datetime, timedelta, timezone
from typing import cast

import pytest
from app.core.config import Settings, get_settings
from app.db import admin
from app.db.admin import drop_and_create_database, validated_name
from app.db.session import unit_of_work
from app.models.base import UtcDateTime
from sqlalchemy.dialects import mssql
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.parametrize("name", ["bus_db", "BusDb2", "a", "_", "bus_db_test", "123"])
def test_validated_name_accepts_letters_digits_and_underscores(name: str) -> None:
    assert validated_name(name) == name


@pytest.mark.parametrize(
    "name",
    ["", "bus db", "bus'db", 'bus"db', "bus;db", "bus-db", "bus_db;DROP", "bus_db\n"],
)
def test_validated_name_rejects_anything_else(name: str) -> None:
    with pytest.raises(ValueError, match="letters, digits, and underscores"):
        validated_name(name)


@pytest.mark.parametrize("name", ["bus_db", "mid_dev", "unit_db_test_x", "test", "_tes"])
def test_drop_and_create_refuses_names_not_ending_in_test_before_connecting(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_connecting(settings: object) -> None:
        raise AssertionError("must not connect for a protected name")

    monkeypatch.setattr(admin, "master_engine", fail_if_connecting)

    with pytest.raises(ValueError, match="_test"):
        drop_and_create_database(get_settings(), name)


def test_drop_and_create_rejects_an_invalid_name_even_when_it_ends_in_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_connecting(settings: object) -> None:
        raise AssertionError("must not connect for an invalid name")

    monkeypatch.setattr(admin, "master_engine", fail_if_connecting)

    with pytest.raises(ValueError, match="letters, digits, and underscores"):
        drop_and_create_database(get_settings(), "bad-name_test")


# SQLAlchemy's mssql.dialect() ships without type hints.
DIALECT = mssql.dialect()  # type: ignore[no-untyped-call]


def test_utc_datetime_rejects_a_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        UtcDateTime().process_bind_param(datetime(2026, 1, 15, 10, 30), DIALECT)


def test_utc_datetime_passes_none_through_unchanged() -> None:
    column = UtcDateTime()

    assert column.process_bind_param(None, DIALECT) is None
    assert column.process_result_value(None, DIALECT) is None


def test_utc_datetime_stores_an_aware_datetime_as_naive_utc() -> None:
    plus_five_thirty = timezone(timedelta(hours=5, minutes=30))
    local = datetime(2026, 1, 15, 16, 0, tzinfo=plus_five_thirty)

    stored = UtcDateTime().process_bind_param(local, DIALECT)

    assert stored == datetime(2026, 1, 15, 10, 30)
    assert stored is not None and stored.tzinfo is None


def test_utc_datetime_returns_a_utc_aware_datetime_on_read() -> None:
    value = UtcDateTime().process_result_value(datetime(2026, 1, 15, 10, 30), DIALECT)

    assert value == datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
    assert value is not None and value.utcoffset() == timedelta(0)


class RecordingSession:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def __enter__(self) -> "RecordingSession":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.calls.append("close")

    def commit(self) -> None:
        self.calls.append("commit")

    def rollback(self) -> None:
        self.calls.append("rollback")


def recording_factory(calls: list[str]) -> sessionmaker[Session]:
    return cast("sessionmaker[Session]", lambda: RecordingSession(calls))


def test_unit_of_work_commits_once_and_never_rolls_back_on_success() -> None:
    calls: list[str] = []

    with unit_of_work(recording_factory(calls)):
        calls.append("work")

    assert calls == ["work", "commit", "close"]


def test_unit_of_work_rolls_back_without_committing_on_failure() -> None:
    calls: list[str] = []

    with pytest.raises(RuntimeError, match="boom"):
        with unit_of_work(recording_factory(calls)):
            raise RuntimeError("boom")

    assert calls == ["rollback", "close"]


def test_admin_wait_probes_the_server_through_probe_master(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probed: list[Settings] = []
    monkeypatch.setattr(admin, "probe_master", probed.append)

    assert admin.main(["wait"]) == 0

    assert len(probed) == 1 and probed[0].db_name == "unit_db"
