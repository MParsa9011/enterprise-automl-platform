"""Dataset and dataset-version data-access repositories."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.models.dataset import Dataset, DatasetVersion
from app.repositories.base import BaseRepository


class DatasetRepository(BaseRepository[Dataset]):
    """Persistence operations for :class:`Dataset` (excludes soft-deleted)."""

    model = Dataset
    searchable_fields = ("name", "slug", "description")

    def _base_conditions(self) -> list[Any]:
        """Exclude soft-deleted datasets from every generated read query."""
        return [Dataset.deleted_at.is_(None)]

    async def get_active(self, dataset_id: uuid.UUID) -> Dataset | None:
        """Return a non-deleted dataset by id, or ``None``."""
        stmt = select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def slug_exists(self, project_id: uuid.UUID, slug: str) -> bool:
        """Return whether ``project_id`` already has a live dataset with ``slug``."""
        stmt = select(Dataset.id).where(
            Dataset.project_id == project_id,
            Dataset.slug == slug,
            Dataset.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).first() is not None


class DatasetVersionRepository(BaseRepository[DatasetVersion]):
    """Persistence operations for :class:`DatasetVersion`."""

    model = DatasetVersion

    async def get_for_dataset(self, dataset_id: uuid.UUID, version: int) -> DatasetVersion | None:
        """Return a specific version of a dataset, or ``None``."""
        stmt = select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset_id,
            DatasetVersion.version == version,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_for_dataset(self, dataset_id: uuid.UUID) -> DatasetVersion | None:
        """Return the highest-numbered version of a dataset, or ``None``."""
        stmt = (
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
