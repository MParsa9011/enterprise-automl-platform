"""Dataset management use-cases.

Handles the full upload pipeline — parse, profile, store, version — and the
dataset lifecycle. Project-level authorization is delegated to
:class:`ProjectService`, keeping a single source of truth for who may touch a
project's resources. Each upload produces a new immutable version, so datasets
are fully reproducible.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import anyio

from app.core.config import settings
from app.core.constants import DatasetFileType
from app.core.exceptions import NotFoundError, UnprocessableEntityError
from app.core.logging import get_logger
from app.core.utils import slugify
from app.ml.io import DataLoadError, detect_file_type, read_tabular
from app.ml.profiling import profile_dataframe
from app.models.dataset import Dataset, DatasetVersion
from app.models.user import User
from app.repositories.dataset import DatasetRepository, DatasetVersionRepository
from app.schemas.dataset import DatasetCreate
from app.schemas.pagination import PageParams
from app.services.project import ProjectService
from app.storage.base import Storage

logger = get_logger(__name__)


class DatasetService:
    """Application service implementing dataset use-cases."""

    def __init__(
        self,
        datasets: DatasetRepository,
        versions: DatasetVersionRepository,
        storage: Storage,
        projects: ProjectService,
    ) -> None:
        self._datasets = datasets
        self._versions = versions
        self._storage = storage
        self._projects = projects

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def create(
        self,
        actor: User,
        project_id: uuid.UUID,
        meta: DatasetCreate,
        *,
        filename: str,
        content: bytes,
    ) -> Dataset:
        """Create a dataset and its first version from an uploaded file."""
        await self._projects.get(actor, project_id)  # authorize project access
        self._check_size(content)

        slug = await self._unique_slug(project_id, meta.name)
        dataset = await self._datasets.create(
            name=meta.name,
            slug=slug,
            description=meta.description,
            project_id=project_id,
            created_by=actor.id,
            latest_version=0,
        )
        await self._create_version(dataset, filename=filename, content=content)
        logger.info("dataset_created", dataset_id=str(dataset.id), project_id=str(project_id))
        return dataset

    async def add_version(
        self,
        actor: User,
        dataset_id: uuid.UUID,
        *,
        filename: str,
        content: bytes,
    ) -> DatasetVersion:
        """Append a new immutable version to an existing dataset."""
        dataset = await self.get(actor, dataset_id)
        self._check_size(content)
        version = await self._create_version(dataset, filename=filename, content=content)
        logger.info(
            "dataset_version_added", dataset_id=str(dataset_id), version=version.version
        )
        return version

    async def delete(self, actor: User, dataset_id: uuid.UUID) -> None:
        """Soft-delete a dataset the actor is authorized to manage."""
        from datetime import UTC, datetime

        dataset = await self.get(actor, dataset_id)
        await self._datasets.update(dataset, deleted_at=datetime.now(UTC))
        logger.info("dataset_deleted", dataset_id=str(dataset_id))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    async def get(self, actor: User, dataset_id: uuid.UUID) -> Dataset:
        """Return a dataset the actor is authorized to access."""
        dataset = await self._datasets.get_active(dataset_id)
        if dataset is None:
            raise NotFoundError("Dataset not found.")
        # Authorize via the owning project; raises NotFound if inaccessible.
        await self._projects.get(actor, dataset.project_id)
        return dataset

    async def list(
        self, actor: User, project_id: uuid.UUID, params: PageParams
    ) -> tuple[Sequence[Dataset], int]:
        """List datasets within a project the actor can access."""
        await self._projects.get(actor, project_id)
        return await self._datasets.list(params, filters={"project_id": project_id})

    async def get_version(
        self, actor: User, dataset_id: uuid.UUID, version: int
    ) -> DatasetVersion:
        """Return a specific dataset version, authorizing access first."""
        await self.get(actor, dataset_id)
        record = await self._versions.get_for_dataset(dataset_id, version)
        if record is None:
            raise NotFoundError(f"Version {version} not found for this dataset.")
        return record

    async def read_content(
        self, actor: User, dataset_id: uuid.UUID, version: int
    ) -> tuple[DatasetVersion, bytes]:
        """Return a version's metadata and raw file bytes."""
        record = await self.get_version(actor, dataset_id, version)
        content = await self._storage.read(record.storage_key)
        return record, content

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _create_version(
        self, dataset: Dataset, *, filename: str, content: bytes
    ) -> DatasetVersion:
        """Parse, profile and persist a new version for ``dataset``."""
        file_type = self._resolve_file_type(filename)
        try:
            frame = await anyio.to_thread.run_sync(read_tabular, content, file_type)
        except DataLoadError as exc:
            raise UnprocessableEntityError(str(exc)) from exc
        profile = await anyio.to_thread.run_sync(profile_dataframe, frame)

        next_version = dataset.latest_version + 1
        storage_key = f"datasets/{dataset.project_id}/{dataset.id}/v{next_version}/{filename}"
        stored = await self._storage.save(storage_key, content, content_type=None)

        version = await self._versions.create(
            dataset_id=dataset.id,
            version=next_version,
            storage_key=storage_key,
            original_filename=filename,
            file_type=file_type,
            size_bytes=stored.size_bytes,
            checksum=stored.checksum,
            n_rows=profile.n_rows,
            n_columns=profile.n_columns,
            columns_schema=profile.columns,
            statistics=profile.statistics,
        )
        await self._datasets.update(dataset, latest_version=next_version)
        return version

    @staticmethod
    def _resolve_file_type(filename: str) -> DatasetFileType:
        """Detect the file type, raising a 422 on unsupported extensions."""
        try:
            return detect_file_type(filename)
        except DataLoadError as exc:
            raise UnprocessableEntityError(str(exc)) from exc

    @staticmethod
    def _check_size(content: bytes) -> None:
        """Reject uploads exceeding the configured maximum size."""
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise UnprocessableEntityError(
                f"File exceeds the maximum upload size of {settings.MAX_UPLOAD_SIZE_MB} MB."
            )
        if not content:
            raise UnprocessableEntityError("Uploaded file is empty.")

    async def _unique_slug(self, project_id: uuid.UUID, name: str) -> str:
        """Generate a dataset slug unique within its project."""
        base = slugify(name)
        candidate = base
        suffix = 2
        while await self._datasets.slug_exists(project_id, candidate):
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate
