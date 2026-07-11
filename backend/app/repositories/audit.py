"""Audit-log data-access repository."""

from __future__ import annotations

from typing import Any

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Append-only persistence for :class:`AuditLog` records."""

    model = AuditLog
    searchable_fields = ("action", "path", "resource_type")

    async def record(self, **data: Any) -> None:
        """Insert an audit entry without flushing a refresh round-trip.

        Audit rows are write-only (the UUID primary key is client-generated), so
        skipping the ``refresh`` that :meth:`BaseRepository.create` performs keeps
        the write to a single statement.
        """
        self.session.add(AuditLog(**data))
        await self.session.flush()
