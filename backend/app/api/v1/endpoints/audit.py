"""Audit-log endpoints (restricted to the ``audit:read`` permission)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import AuditServiceDep, require_permissions
from app.models.user import User
from app.schemas.notification import AuditLogRead
from app.schemas.pagination import Page, PageParams

router = APIRouter(prefix="/audit-logs", tags=["audit"])

AuditReader = Annotated[User, Depends(require_permissions("audit:read"))]
Pagination = Annotated[PageParams, Query()]


@router.get("", response_model=Page[AuditLogRead], summary="List audit logs")
async def list_audit_logs(
    actor: AuditReader,
    service: AuditServiceDep,
    params: Pagination,
) -> Page[AuditLogRead]:
    """Return a paginated, newest-first list of audit-log entries."""
    items, total = await service.list(params)
    return Page.create(
        items=[AuditLogRead.model_validate(entry) for entry in items],
        total=total,
        params=params,
    )
