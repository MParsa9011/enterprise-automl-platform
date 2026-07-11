"""Prediction use-cases.

Loads a registered model's persisted pipeline and serves predictions for a batch
of JSON records. Incoming records are validated against the model's stored
feature schema and coerced to the expected dtypes, so the exact preprocessing +
estimator pipeline that was trained is applied at serving time.
"""

from __future__ import annotations

import uuid
from functools import partial
from typing import Any

import anyio
import pandas as pd

from app.core.constants import TaskType
from app.core.exceptions import UnprocessableEntityError
from app.models.model import Model
from app.models.user import User
from app.ml.training import load_model
from app.repositories.model import ModelRepository
from app.schemas.prediction import PredictionItem, PredictionResponse
from app.services.project import ProjectService
from app.storage.base import Storage


class PredictionService:
    """Application service for serving model predictions."""

    def __init__(
        self,
        models: ModelRepository,
        projects: ProjectService,
        storage: Storage,
    ) -> None:
        self._models = models
        self._projects = projects
        self._storage = storage

    async def predict(
        self, actor: User, model_id: uuid.UUID, records: list[dict[str, Any]]
    ) -> PredictionResponse:
        """Run predictions for ``records`` against a registered model."""
        model = await self._models.get_active(model_id)
        if model is None:
            raise UnprocessableEntityError("Model not found.")
        await self._projects.get(actor, model.project_id)  # authorize

        frame = self._build_frame(records, model.feature_schema)
        artifact = await self._storage.read(model.artifact_key)
        pipeline = await anyio.to_thread.run_sync(load_model, artifact)

        predictions = await anyio.to_thread.run_sync(
            partial(self._run, pipeline, frame, model)
        )
        return PredictionResponse(
            model_id=str(model.id),
            model_version=model.version,
            task_type=str(model.task_type),
            predictions=predictions,
        )

    # ------------------------------------------------------------------
    # Internals (sync, run in a worker thread)
    # ------------------------------------------------------------------
    @staticmethod
    def _run(pipeline: Any, frame: pd.DataFrame, model: Model) -> list[PredictionItem]:
        """Predict and, for classifiers, attach class probabilities."""
        raw = pipeline.predict(frame)
        task_type = TaskType(model.task_type)
        class_names = model.class_names or []

        if task_type == TaskType.CLASSIFICATION:
            labels = [PredictionService._decode_label(v, class_names) for v in raw]
            proba = (
                pipeline.predict_proba(frame)
                if hasattr(pipeline, "predict_proba")
                else None
            )
            items = []
            for i, label in enumerate(labels):
                probabilities = None
                if proba is not None and class_names:
                    probabilities = {
                        class_names[j]: float(proba[i][j]) for j in range(len(class_names))
                    }
                items.append(PredictionItem(prediction=label, probabilities=probabilities))
            return items

        return [PredictionItem(prediction=float(v)) for v in raw]

    @staticmethod
    def _decode_label(value: Any, class_names: list[str]) -> Any:
        """Map an encoded class index back to its original label when possible."""
        try:
            index = int(value)
        except (TypeError, ValueError):
            return value
        if 0 <= index < len(class_names):
            return class_names[index]
        return value

    @staticmethod
    def _build_frame(
        records: list[dict[str, Any]], feature_schema: list[dict[str, str]]
    ) -> pd.DataFrame:
        """Validate records against the schema and build a typed dataframe."""
        if not feature_schema:
            raise UnprocessableEntityError("Model has no feature schema to validate against.")
        names = [column["name"] for column in feature_schema]

        for i, record in enumerate(records):
            missing = [name for name in names if name not in record]
            if missing:
                raise UnprocessableEntityError(
                    f"Record {i} is missing required features: {missing}."
                )

        frame = pd.DataFrame([{name: record.get(name) for name in names} for record in records])
        for column in feature_schema:
            dtype = column["dtype"]
            if "int" in dtype or "float" in dtype:
                frame[column["name"]] = pd.to_numeric(frame[column["name"]], errors="coerce")
        return frame
