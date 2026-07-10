"""Metadata aggregator for Alembic autogeneration.

Alembic compares the live database against ``Base.metadata`` to emit migrations.
For that comparison to be complete, *every* ORM model must be imported so its
table is registered on the shared metadata. This module is the single place that
imports them all; new models must be added here as they are created.
"""

from __future__ import annotations

from app.db.base_class import Base

# NOTE: model imports are added below as features land. They are intentionally
# imported for their side effect (table registration) only.
# Example:
#   from app.models.user import User  # noqa: F401

__all__ = ["Base"]
