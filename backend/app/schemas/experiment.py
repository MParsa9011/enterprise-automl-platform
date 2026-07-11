"""Experiment and run data-transfer objects."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field, model_validator

from app.core.constants import ExperimentStatus, RunStatus, TaskType
from app.schemas.base import Schema, TimestampedSchema
from app.schemas.features import FeatureConfigIn


class ExperimentCreate(Schema):
    """Payload to configure and launch an AutoML experiment."""

    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    dataset_id: uuid.UUID
    dataset_version: int | None = Field(
        default=None, ge=1, description="Defaults to the dataset's latest version."
    )
    task_type: TaskType
    target_column: str | None = Field(
        default=None, description="Required for classification and regression."
    )
    primary_metric: str | None = Field(
        default=None, description="Defaults to a sensible metric for the task."
    )
    algorithms: list[str] | None = Field(
        default=None, description="Defaults to all algorithms available for the task."
    )
    feature_config: FeatureConfigIn = Field(default_factory=FeatureConfigIn)

    optimize: bool = False
    n_trials: int = Field(default=20, ge=1, le=200)
    cv_folds: int = Field(default=3, ge=2, le=10)
    test_size: float = Field(default=0.2, gt=0.0, lt=0.9)

    @model_validator(mode="after")
    def _require_target_for_supervised(self) -> ExperimentCreate:
        """Supervised tasks require a target column."""
        supervised = (TaskType.CLASSIFICATION, TaskType.REGRESSION)
        if self.task_type in supervised and not self.target_column:
            raise ValueError("target_column is required for classification/regression.")
        return self


class RunRead(TimestampedSchema):
    """A single algorithm training run (without heavy figure payloads)."""

    id: uuid.UUID
    experiment_id: uuid.UUID
    algorithm: str
    status: RunStatus
    primary_score: float | None
    metrics: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    duration_seconds: float | None
    error_message: str | None


class RunDetail(RunRead):
    """A run including its evaluation figures."""

    figures: dict[str, Any] = Field(default_factory=dict)


class ExperimentRead(TimestampedSchema):
    """Experiment summary."""

    id: uuid.UUID
    name: str
    description: str | None
    project_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version: int
    task_type: TaskType
    target_column: str | None
    primary_metric: str
    algorithms: list[str] = Field(default_factory=list)
    status: ExperimentStatus
    best_run_id: uuid.UUID | None
    optimize: bool
    n_trials: int
    cv_folds: int
    test_size: float
    error_message: str | None


class ExperimentDetail(ExperimentRead):
    """Experiment including its runs."""

    runs: list[RunRead] = Field(default_factory=list)


class RunExplanation(Schema):
    """Explainability payload for a trained run."""

    permutation_importance: dict[str, Any]
    shap: dict[str, Any] | None = None
