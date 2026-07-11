"""Audit-log query use-cases (writes happen in middleware)."""

from __future__ import annotations

from collections.abc import Sequence

from app.models.audit import AuditLog
from app.repositories.audit import AuditLogRepository
from app.schemas.pagination import PageParams


class AuditService:
    """Read-side application service for the audit trail (admin only)."""

    def __init__(self, audit_logs: AuditLogRepository) -> None:
        self._audit_logs = audit_logs

    async def list(self, params: PageParams) -> tuple[Sequence[AuditLog], int]:
        """List audit-log entries, newest first."""
        return await self._audit_logs.list(params)
