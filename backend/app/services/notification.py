"""Notification use-cases."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from app.core.constants import NotificationType
from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification import NotificationRepository
from app.schemas.pagination import PageParams


class NotificationService:
    """Application service for in-app notifications."""

    def __init__(self, notifications: NotificationRepository) -> None:
        self._notifications = notifications

    async def create(
        self,
        user_id: uuid.UUID,
        *,
        type: NotificationType,
        title: str,
        message: str,
        link: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Notification:
        """Create a notification addressed to a user."""
        return await self._notifications.create(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
            meta=meta or {},
        )

    async def list(
        self, actor: User, params: PageParams, *, unread_only: bool = False
    ) -> tuple[Sequence[Notification], int]:
        """List the actor's notifications, most recent first."""
        items, total = await self._notifications.list(params, filters={"user_id": actor.id})
        if unread_only:
            items = [n for n in items if n.read_at is None]
            total = await self._notifications.unread_count(actor.id)
        return items, total

    async def unread_count(self, actor: User) -> int:
        """Return the actor's unread notification count."""
        return await self._notifications.unread_count(actor.id)

    async def mark_read(self, actor: User, notification_id: uuid.UUID) -> Notification:
        """Mark one of the actor's notifications as read."""
        notification = await self._notifications.get(notification_id)
        if notification is None or notification.user_id != actor.id:
            raise NotFoundError("Notification not found.")
        return await self._notifications.mark_read(notification)

    async def mark_all_read(self, actor: User) -> int:
        """Mark all of the actor's notifications as read."""
        return await self._notifications.mark_all_read(actor.id)
