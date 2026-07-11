"""Registered model.

A :class:`Model` is an immutable, versioned promotion of a completed training
:class:`~app.models.experiment.Run` into a project's registry. It copies the
metrics, feature schema and artifact reference needed to serve predictions
independently of the experiment, so serving never depends on experiment state.
Deployment is expressed via the :class:`~app.core.constants.ModelStage` lifecycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ModelStage, TaskType
from app.db.base_class import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Model(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A versioned, deployable model in a project's registry."""

    __table_args__ = (
        UniqueConstraint("project_id", "slug", "version", name="uq_models_project_slug_version"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    experiment_id: Mapped[UUID] = mapped_column(
        ForeignKey("experiments.id", ondelete="SET NULL"), nullable=True
    )
    run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)

    stage: Mapped[ModelStage] = mapped_column(
        String(20), default=ModelStage.NONE, nullable=False, index=True
    )
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    task_type: Mapped[TaskType] = mapped_column(String(20), nullable=False)
    target_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_metric: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    feature_schema: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    class_names: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    artifact_key: Mapped[str] = mapped_column(String(512), nullable=False)

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    project: Mapped[Project] = relationship(lazy="joined")

    @property
    def is_deployed(self) -> bool:
        """Whether the model is the active production model."""
        return self.stage == ModelStage.PRODUCTION

    def __repr__(self) -> str:
        return f"<Model {self.slug} v{self.version} stage={self.stage}>"
