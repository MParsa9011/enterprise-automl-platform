"""Project data-access repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Persistence operations for :class:`Project`.

    All reads exclude soft-deleted rows by default so callers never have to
    remember to filter them out.
    """

    model = Project
    searchable_fields = ("name", "slug", "description")

    def _base_conditions(self) -> list[Any]:
        """Exclude soft-deleted projects from every generated read query."""
        return [Project.deleted_at.is_(None)]

    async def get_active(self, project_id: uuid.UUID) -> Project | None:
        """Return a non-deleted project by id, or ``None``."""
        stmt = select(Project).where(
            Project.id == project_id,
            Project.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def slug_exists(self, owner_id: uuid.UUID, slug: str) -> bool:
        """Return whether ``owner_id`` already has a live project with ``slug``."""
        stmt = select(Project.id).where(
            Project.owner_id == owner_id,
            Project.slug == slug,
            Project.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.first() is not None
