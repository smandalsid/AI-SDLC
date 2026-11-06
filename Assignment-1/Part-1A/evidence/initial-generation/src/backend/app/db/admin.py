import argparse
import re
from collections.abc import Sequence
from functools import partial

from sqlalchemy import Engine, create_engine, text

from app.core.config import Settings, get_settings
from app.db.session import wait_for_database

IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def validated_name(name: str) -> str:
    if not IDENTIFIER.fullmatch(name):
        raise ValueError("database name may only contain letters, digits, and underscores")
    return name


def master_engine(settings: Settings) -> Engine:
    return create_engine(settings.database_url("master"), isolation_level="AUTOCOMMIT")


def probe_master(settings: Settings) -> None:
    """The server answers on master even before the application database exists."""
    engine = master_engine(settings)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()


def create_database_if_missing(settings: Settings, name: str) -> None:
    validated_name(name)
    engine = master_engine(settings)
    quoted = engine.dialect.identifier_preparer.quote(name)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM sys.databases WHERE name = :name"), {"name": name}
        ).first()
        if exists is None:
            connection.execute(text(f"CREATE DATABASE {quoted}"))
    engine.dispose()


def drop_and_create_database(settings: Settings, name: str) -> None:
    """Recreate a test database; refuses any name that does not end in `_test`."""
    validated_name(name)
    if not name.endswith("_test"):
        raise ValueError("refusing to drop a database whose name does not end in _test")
    engine = master_engine(settings)
    quoted = engine.dialect.identifier_preparer.quote(name)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM sys.databases WHERE name = :name"), {"name": name}
        ).first()
        if exists is not None:
            connection.execute(
                text(f"ALTER DATABASE {quoted} SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
            )
            connection.execute(text(f"DROP DATABASE {quoted}"))
        connection.execute(text(f"CREATE DATABASE {quoted}"))
    engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Database administration for local development")
    parser.add_argument("command", choices=["wait", "create", "recreate"])
    parser.add_argument(
        "--database", help="defaults to DB_NAME (create) or DB_NAME_test (recreate)"
    )
    args = parser.parse_args(argv)
    settings = get_settings()

    if args.command == "wait":
        wait_for_database(partial(probe_master, settings))
    elif args.command == "create":
        create_database_if_missing(settings, args.database or settings.db_name)
    else:
        drop_and_create_database(settings, args.database or settings.test_database_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
