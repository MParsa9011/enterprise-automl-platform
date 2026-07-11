"""Notification data-access repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Persistence operations for :class:`Notification`."""

    model = Notification
    searchable_fields = ("title", "message")

    async def unread_count(self, user_id: uuid.UUID) -> int:
        """Return the number of unread notifications for a user."""
        stmt = select(func.count()).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def mark_read(self, notification: Notification) -> Notification:
        """Mark a single notification as read (idempotent).

        Uses :meth:`~BaseRepository.update`, which refreshes the row after the
        write so server-updated columns (``updated_at``) are reloaded inside the
        async context and remain safe to serialise.
        """
        if notification.read_at is not None:
            return notification
        return await self.update(notification, read_at=datetime.now(UTC))

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """Mark all of a user's notifications as read; return the count updated."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
