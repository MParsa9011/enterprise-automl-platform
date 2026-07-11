"""Dataset and dataset-version models.

A :class:`Dataset` is a named, versioned tabular resource inside a project. Each
upload creates an immutable :class:`DatasetVersion` that records the stored file,
its schema and a computed statistical profile. Immutable versions give the
platform reproducibility — an experiment always references the exact version it
trained on, even after newer data is uploaded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DatasetFileType
from app.db.base_class import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Dataset(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A named, versioned tabular dataset within a project."""

    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_datasets_project_id_slug"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Denormalised pointer to the highest version number for cheap listing.
    latest_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project: Mapped["Project"] = relationship(lazy="joined")
    versions: Mapped[list["DatasetVersion"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetVersion.version.desc()",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Dataset {self.slug} project={self.project_id}>"


class DatasetVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An immutable snapshot of an uploaded dataset file plus its profile."""

    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_dataset_versions_dataset_id_version"),
    )

    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Stored file metadata ---
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[DatasetFileType] = mapped_column(String(20), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # --- Shape & schema ---
    n_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    n_columns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    columns_schema: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    statistics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    dataset: Mapped["Dataset"] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<DatasetVersion dataset={self.dataset_id} v{self.version}>"
