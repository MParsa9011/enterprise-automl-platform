"""Reusable ORM mixins.

These mixins compose the common columns shared by nearly every table — a UUID
primary key and audit timestamps — so individual models stay focused on their
domain-specific fields. Keeping them here avoids duplicating column definitions
across a dozen models and guarantees consistent types and defaults.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Adds a server-generated UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` audit columns.

    Timestamps are populated by the database (``func.now()``) so they remain
    correct regardless of application-server clock skew, and ``updated_at`` is
    refreshed automatically on every UPDATE via ``onupdate``.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds a nullable ``deleted_at`` column for soft deletes."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        """True when the row has been soft-deleted."""
        return self.deleted_at is not None
