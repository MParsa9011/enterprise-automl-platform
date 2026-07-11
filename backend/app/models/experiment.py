"""Experiment and Run models.

An :class:`Experiment` captures a training request — a dataset version, target,
feature configuration and the set of algorithms to try. Executing it fans out
into one :class:`Run` per algorithm; each run trains, tunes and evaluates a model
and records its metrics and a persisted artifact. The best run (by the primary
metric) is referenced from the experiment.

``Experiment.best_run_id`` is an unconstrained UUID rather than a foreign key to
avoid a circular FK dependency with ``runs.experiment_id`` (which SQLite cannot
resolve via ALTER); referential integrity for it is enforced in the service.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ExperimentStatus, RunStatus, TaskType
from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.project import Project


class Experiment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A configured AutoML training job over a dataset version."""

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False)

    task_type: Mapped[TaskType] = mapped_column(String(20), nullable=False)
    target_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    feature_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    algorithms: Mapped[list[str]] = mapped_column(JSON, default=list)
    primary_metric: Mapped[str] = mapped_column(String(50), nullable=False)

    # Training controls.
    optimize: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    n_trials: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    cv_folds: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    test_size: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    random_state: Mapped[int] = mapped_column(Integer, default=42, nullable=False)

    status: Mapped[ExperimentStatus] = mapped_column(
        String(20), default=ExperimentStatus.DRAFT, nullable=False, index=True
    )
    best_run_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    project: Mapped[Project] = relationship(lazy="joined")
    dataset: Mapped[Dataset] = relationship(lazy="joined")
    runs: Mapped[list[Run]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="Run.created_at",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Experiment {self.name} status={self.status}>"


class Run(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single algorithm's training/evaluation within an experiment."""

    experiment_id: Mapped[UUID] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        String(20), default=RunStatus.PENDING, nullable=False, index=True
    )

    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    figures: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Input contract for serving: the feature columns the model expects and, for
    # classifiers, the ordered class labels the encoded predictions map back to.
    feature_schema: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    class_names: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    # Primary metric value, denormalised for cheap ranking/sorting of runs.
    primary_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    artifact_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    experiment: Mapped[Experiment] = relationship(back_populates="runs")

    def __repr__(self) -> str:
        return f"<Run {self.algorithm} status={self.status} score={self.primary_score}>"
