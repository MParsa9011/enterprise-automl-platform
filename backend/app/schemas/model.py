"""Model-registry data-transfer objects."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from app.core.constants import ModelStage, TaskType
from app.schemas.base import Schema, TimestampedSchema


class ModelRegister(Schema):
    """Payload to promote a completed run into the registry."""

    run_id: uuid.UUID
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    deploy: bool = Field(default=False, description="Deploy to production on register.")


class ModelRead(TimestampedSchema):
    """Registered-model representation."""

    id: uuid.UUID
    name: str
    slug: str
    version: int
    description: str | None
    project_id: uuid.UUID
    experiment_id: uuid.UUID | None
    run_id: uuid.UUID
    stage: ModelStage
    algorithm: str
    task_type: TaskType
    target_column: str | None
    primary_metric: str
    primary_score: float | None
    metrics: dict[str, Any] = Field(default_factory=dict)
    feature_schema: list[dict[str, str]] = Field(default_factory=list)
    class_names: list[str] | None = None


class ModelStageUpdate(Schema):
    """Payload to change a model's registry stage."""

    stage: ModelStage


class ModelComparison(Schema):
    """Side-by-side comparison of several models' metrics."""

    models: list[ModelRead]
    metrics: list[str]
