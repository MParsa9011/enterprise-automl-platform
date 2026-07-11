"""Notification data-transfer objects."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.constants import NotificationType
from app.schemas.base import Schema, TimestampedSchema
from app.schemas.pagination import PageParams


class NotificationQuery(PageParams):
    """Pagination plus a notification-specific unread filter.

    Combined into one query model because FastAPI query-parameter models cannot
    be mixed with additional standalone scalar query parameters on one endpoint.
    """

    unread_only: bool = False


class NotificationRead(TimestampedSchema):
    """A user notification."""

    id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    link: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    read_at: datetime | None = None


class UnreadCount(Schema):
    """Count of unread notifications."""

    unread: int


class AuditLogRead(TimestampedSchema):
    """A single audit-log entry."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    method: str
    path: str
    status_code: int
    ip_address: str | None
    request_id: str | None
