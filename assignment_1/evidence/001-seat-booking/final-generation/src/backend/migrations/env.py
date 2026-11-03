from alembic import context
from app.core.config import get_settings
from app.models import Base
from sqlalchemy import create_engine, pool

config = context.config


def target_database() -> str:
    """The database to migrate: config.attributes (tests), then `-x database=NAME`, then DB_NAME."""
    override = config.attributes.get("database") or context.get_x_argument(as_dictionary=True).get(
        "database"
    )
    return str(override or get_settings().db_name)


def run_migrations_online() -> None:
    engine = create_engine(get_settings().database_url(target_database()), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("offline migrations are not supported; the URL is built from the settings")
run_migrations_online()
