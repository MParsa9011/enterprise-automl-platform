"""Notification endpoints for the authenticated user."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, NotificationServiceDep
from app.schemas.notification import NotificationQuery, NotificationRead, UnreadCount
from app.schemas.pagination import Page
from app.schemas.response import MessageResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationRead], summary="List notifications")
async def list_notifications(
    current_user: CurrentUser,
    service: NotificationServiceDep,
    query: Annotated[NotificationQuery, Query()],
) -> Page[NotificationRead]:
    """Return the current user's notifications, most recent first."""
    items, total = await service.list(current_user, query, unread_only=query.unread_only)
    return Page.create(
        items=[NotificationRead.model_validate(n) for n in items],
        total=total,
        params=query,
    )


@router.get("/unread-count", response_model=UnreadCount, summary="Unread count")
async def unread_count(
    current_user: CurrentUser,
    service: NotificationServiceDep,
) -> UnreadCount:
    """Return the number of unread notifications for the current user."""
    return UnreadCount(unread=await service.unread_count(current_user))


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="Mark a notification read",
)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    service: NotificationServiceDep,
) -> NotificationRead:
    """Mark a single notification as read."""
    notification = await service.mark_read(current_user, notification_id)
    return NotificationRead.model_validate(notification)


@router.post("/read-all", response_model=MessageResponse, summary="Mark all read")
async def mark_all_read(
    current_user: CurrentUser,
    service: NotificationServiceDep,
) -> MessageResponse:
    """Mark all of the current user's notifications as read."""
    count = await service.mark_all_read(current_user)
    return MessageResponse(message="All notifications marked read.", detail=f"{count} updated")
