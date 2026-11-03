import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import DatabaseUnavailableError


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url(settings.db_name), pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(get_engine(), expire_on_commit=False)


@contextmanager
def unit_of_work(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Commit when the block succeeds, roll back on any exception."""
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_session() -> Iterator[Session]:
    with unit_of_work(get_session_factory()) as session:
        yield session


def probe_database() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


def wait_for_database(
    probe: Callable[[], None] | None = None,
    *,
    timeout_seconds: float = 60,
    interval_seconds: float = 1,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> None:
    """Retry the probe until it succeeds; raise DatabaseUnavailableError after the timeout."""
    check = probe or probe_database
    deadline = monotonic() + timeout_seconds
    while True:
        try:
            check()
            return
        except Exception as error:
            if monotonic() >= deadline:
                raise DatabaseUnavailableError(
                    "the database did not accept queries in time"
                ) from error
            sleep(interval_seconds)
