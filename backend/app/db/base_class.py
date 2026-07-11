"""SQLAlchemy declarative base.

A consistent constraint-naming convention is configured on the shared metadata so
that Alembic produces deterministic, human-readable migration names (essential
for reviewable, conflict-free migration history). ``__tablename__`` is derived
automatically from the class name unless a subclass overrides it.
"""

from __future__ import annotations

import re

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

# Deterministic naming convention for indexes, constraints and keys.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

_CAMEL_TO_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        """Derive a snake_case, pluralised table name from the class name."""
        snake = _CAMEL_TO_SNAKE.sub("_", cls.__name__).lower()
        return snake if snake.endswith("s") else f"{snake}s"

    def __repr__(self) -> str:
        pk = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={pk}>"
