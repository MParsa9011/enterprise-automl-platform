"""Notification model.

Lightweight per-user, in-app notifications emitted on significant events
(experiment completion, model deployment, ...). ``read_at`` is nullable so unread
notifications are cheap to count and filter.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import NotificationType
from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An in-app notification addressed to a single user."""

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        String(20), default=NotificationType.INFO, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_read(self) -> bool:
        """Whether the notification has been read."""
        return self.read_at is not None

    def __repr__(self) -> str:
        return f"<Notification {self.type} user={self.user_id}>"
