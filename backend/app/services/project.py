"""Project (workspace) use-cases.

Encapsulates project lifecycle operations and their authorization rules: a user
may only see and mutate their own projects, while superusers may access any.
Cross-owner access returns *not found* rather than *forbidden* so the API does
not leak the existence of other users' projects.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.utils import slugify
from app.models.project import Project
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.schemas.pagination import PageParams
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = get_logger(__name__)


class ProjectService:
    """Application service implementing project use-cases."""

    def __init__(self, projects: ProjectRepository) -> None:
        self._projects = projects

    async def create(self, actor: User, data: ProjectCreate) -> Project:
        """Create a project owned by ``actor`` with a unique slug."""
        slug = await self._unique_slug(actor.id, data.name)
        project = await self._projects.create(
            name=data.name,
            slug=slug,
            description=data.description,
            owner_id=actor.id,
        )
        logger.info("project_created", project_id=str(project.id), owner_id=str(actor.id))
        return project

    async def get(self, actor: User, project_id: uuid.UUID) -> Project:
        """Return a project the actor is authorized to view."""
        project = await self._projects.get_active(project_id)
        if project is None or not self._can_access(actor, project):
            raise NotFoundError("Project not found.")
        return project

    async def list(self, actor: User, params: PageParams) -> tuple[Sequence[Project], int]:
        """List projects visible to the actor (own projects, or all for admin)."""
        filters = {} if actor.is_superuser else {"owner_id": actor.id}
        return await self._projects.list(params, filters=filters)

    async def update(self, actor: User, project_id: uuid.UUID, data: ProjectUpdate) -> Project:
        """Apply a partial update, regenerating the slug if the name changes."""
        project = await self.get(actor, project_id)
        changes = data.model_dump(exclude_unset=True)

        if "name" in changes and changes["name"] != project.name:
            changes["slug"] = await self._unique_slug(
                project.owner_id, changes["name"], exclude_id=project.id
            )

        updated = await self._projects.update(project, **changes)
        logger.info("project_updated", project_id=str(project.id))
        return updated

    async def delete(self, actor: User, project_id: uuid.UUID) -> None:
        """Soft-delete a project the actor owns."""
        project = await self.get(actor, project_id)
        await self._projects.update(project, deleted_at=datetime.now(UTC))
        logger.info("project_deleted", project_id=str(project.id))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _can_access(actor: User, project: Project) -> bool:
        """Whether ``actor`` may access ``project``."""
        return actor.is_superuser or project.owner_id == actor.id

    async def _unique_slug(
        self,
        owner_id: uuid.UUID,
        name: str,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> str:
        """Generate a slug unique within the owner's projects.

        Appends an incrementing numeric suffix on collision (``report``,
        ``report-2``, ``report-3``, ...).
        """
        base = slugify(name)
        candidate = base
        suffix = 2
        while await self._slug_taken(owner_id, candidate, exclude_id):
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    async def _slug_taken(
        self,
        owner_id: uuid.UUID,
        slug: str,
        exclude_id: uuid.UUID | None,
    ) -> bool:
        """Whether ``slug`` is taken by another live project of the owner."""
        existing = await self._projects.get_by(owner_id=owner_id, slug=slug)
        if existing is None:
            return False
        return existing.id != exclude_id
