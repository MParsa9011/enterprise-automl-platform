"""Schema-level invariants for the ORM models.

These guard against classes of bugs that a SQLite-backed integration test cannot
catch because SQLite ignores column type nuances that PostgreSQL enforces.
"""

from __future__ import annotations

import pytest
from sqlalchemy import DateTime

from app.db.base import Base

pytestmark = pytest.mark.unit


def test_all_datetime_columns_are_timezone_aware() -> None:
    """Every timestamp column must be ``TIMESTAMP WITH TIME ZONE``.

    The application always works in tz-aware UTC; a naive column causes
    asyncpg/PostgreSQL to reject inserts ("can't subtract offset-naive and
    offset-aware datetimes"), even though SQLite would silently accept them.
    """
    offenders: list[str] = []
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, DateTime) and not column.type.timezone:
                offenders.append(f"{table.name}.{column.name}")
    assert not offenders, f"Naive DateTime columns found: {offenders}"


def test_every_table_has_a_primary_key() -> None:
    """Sanity check: no table is accidentally missing a primary key."""
    missing = [t.name for t in Base.metadata.tables.values() if not t.primary_key.columns]
    assert not missing, f"Tables without a primary key: {missing}"
