"""Alembic migration environment.

Runs migrations in "online" mode against a synchronous engine built from the
application's settings. Using the sync (psycopg) DSN keeps Alembic simple and
avoids the complexity of driving an async engine for what is a batch operation.
Autogeneration compares the live schema against ``Base.metadata``.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import the aggregated metadata (registers every model's table).
from app.core.config import settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The database URL defaults to the application's sync (psycopg) DSN, but can be
# overridden via ``ALEMBIC_DATABASE_URL`` — useful for autogenerating against a
# throwaway SQLite database in environments without a running Postgres.
database_url = os.getenv("ALEMBIC_DATABASE_URL") or settings.sync_database_uri
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emits SQL to stdout)."""
    context.configure(
        url=settings.sync_database_uri,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
