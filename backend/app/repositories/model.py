"""Model-registry data-access repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select

from app.core.constants import ModelStage
from app.models.model import Model
from app.repositories.base import BaseRepository


class ModelRepository(BaseRepository[Model]):
    """Persistence operations for registered :class:`Model` records."""

    model = Model
    searchable_fields = ("name", "slug", "algorithm", "description")

    def _base_conditions(self) -> list[Any]:
        """Exclude soft-deleted models from every generated read query."""
        return [Model.deleted_at.is_(None)]

    async def get_active(self, model_id: uuid.UUID) -> Model | None:
        """Return a non-deleted model by id, or ``None``."""
        stmt = select(Model).where(Model.id == model_id, Model.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def next_version(self, project_id: uuid.UUID, slug: str) -> int:
        """Return the next version number for a model name within a project."""
        stmt = select(func.max(Model.version)).where(
            Model.project_id == project_id, Model.slug == slug
        )
        current = (await self.session.execute(stmt)).scalar_one_or_none()
        return int(current or 0) + 1

    async def get_production(self, project_id: uuid.UUID, slug: str) -> Model | None:
        """Return the current production model for a name, or ``None``."""
        stmt = select(Model).where(
            Model.project_id == project_id,
            Model.slug == slug,
            Model.stage == ModelStage.PRODUCTION,
            Model.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
