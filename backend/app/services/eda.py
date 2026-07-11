"""EDA and feature-engineering use-cases.

Loads a dataset version through :class:`DatasetService` (which enforces access
control), parses it and runs the framework-agnostic EDA / feature engines off the
event loop. CPU-bound work is dispatched to a worker thread so a large dataset
never blocks the API.
"""

from __future__ import annotations

import uuid
from typing import Any

import anyio
import pandas as pd

from app.core.constants import DatasetFileType
from app.core.exceptions import UnprocessableEntityError
from app.ml.eda import generate_eda
from app.ml.features import FeatureConfig, FeatureConfigError, preview_features
from app.ml.io import DataLoadError, read_tabular
from app.models.user import User
from app.services.dataset import DatasetService


class EdaService:
    """Application service for EDA and feature-preview use-cases."""

    def __init__(self, datasets: DatasetService) -> None:
        self._datasets = datasets

    async def generate(
        self, actor: User, dataset_id: uuid.UUID, version: int
    ) -> dict[str, Any]:
        """Return the EDA figure bundle for a dataset version."""
        frame = await self._load_frame(actor, dataset_id, version)
        return await anyio.to_thread.run_sync(generate_eda, frame)

    async def preview_features(
        self,
        actor: User,
        dataset_id: uuid.UUID,
        version: int,
        config: FeatureConfig,
    ) -> dict[str, Any]:
        """Fit the configured pipeline on a dataset version and summarise output."""
        frame = await self._load_frame(actor, dataset_id, version)
        if config.target and config.target not in frame.columns:
            raise UnprocessableEntityError(
                f"Target column {config.target!r} is not present in the dataset."
            )
        try:
            return await anyio.to_thread.run_sync(preview_features, frame, config)
        except (FeatureConfigError, ValueError) as exc:
            raise UnprocessableEntityError(str(exc)) from exc

    async def _load_frame(
        self, actor: User, dataset_id: uuid.UUID, version: int
    ) -> pd.DataFrame:
        """Authorize, fetch and parse a dataset version into a dataframe."""
        record, content = await self._datasets.read_content(actor, dataset_id, version)
        file_type = DatasetFileType(record.file_type)
        try:
            return await anyio.to_thread.run_sync(read_tabular, content, file_type)
        except DataLoadError as exc:  # pragma: no cover - stored files are valid
            raise UnprocessableEntityError(str(exc)) from exc
