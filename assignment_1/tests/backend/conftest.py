from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from secrets import token_urlsafe

import pytest
from alembic import command
from alembic.config import Config
from app.api.deps import get_clock
from app.core.clock import Clock
from app.core.config import Settings, get_settings
from app.core.passwords import Argon2Hasher
from app.db.admin import drop_and_create_database
from app.db.seed import USERS, reset_data
from app.db.session import get_session, unit_of_work
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "src" / "backend" / "alembic.ini"
FIXED_NOW = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def test_database(settings: Settings) -> str:
    name = settings.test_database_name
    assert name.endswith("_test"), "tests must only ever run against a *_test database"
    drop_and_create_database(settings, name)
    config = Config(str(ALEMBIC_INI))
    config.attributes["database"] = name
    command.upgrade(config, "head")
    return name


@pytest.fixture(scope="session")
def engine(settings: Settings, test_database: str) -> Iterator[Engine]:
    engine = create_engine(settings.database_url(test_database), pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def credentials() -> Mapping[str, str]:
    """A random password per seeded username, kept in memory only and never printed."""
    return {str(user["username"]): token_urlsafe(16) for user in USERS}


@pytest.fixture(scope="session")
def password_hasher() -> Argon2Hasher:
    return Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1)


@pytest.fixture(scope="session")
def password_hashes(
    credentials: Mapping[str, str], password_hasher: Argon2Hasher
) -> Mapping[str, str]:
    return {username: password_hasher.hash(password) for username, password in credentials.items()}


@pytest.fixture(autouse=True)
def reset_database(request: pytest.FixtureRequest) -> None:
    """Every test outside unit/ starts from the seeded state (real commits are needed)."""
    if "unit" in request.node.path.parts:
        return
    factory: sessionmaker[Session] = request.getfixturevalue("session_factory")
    hashes: Mapping[str, str] = request.getfixturevalue("password_hashes")
    with factory() as session:
        reset_data(session, hashes)
        session.commit()


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def app(session_factory: sessionmaker[Session], fake_clock: FakeClock) -> Iterator[FastAPI]:
    application = create_app(wait_for_db=lambda: None)

    def override_session() -> Iterator[Session]:
        with unit_of_work(session_factory) as session:
            yield session

    def override_clock() -> Clock:
        return fake_clock

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_clock] = override_clock
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
