"""Dataset data-transfer objects."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from app.core.constants import DatasetFileType
from app.schemas.base import Schema, TimestampedSchema


class DatasetCreate(Schema):
    """Metadata supplied alongside a dataset file upload."""

    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class DatasetUpdate(Schema):
    """Partial update for dataset metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class ColumnSchema(Schema):
    """Inferred schema for a single dataset column."""

    name: str
    dtype: str
    inferred_type: str
    n_missing: int
    missing_pct: float
    n_unique: int


class DatasetVersionRead(TimestampedSchema):
    """A single immutable dataset version."""

    id: uuid.UUID
    version: int
    original_filename: str
    file_type: DatasetFileType
    size_bytes: int
    checksum: str
    n_rows: int
    n_columns: int
    columns_schema: list[ColumnSchema] = Field(default_factory=list)


class DatasetVersionDetail(DatasetVersionRead):
    """A dataset version including its full statistics document."""

    statistics: dict[str, Any] = Field(default_factory=dict)


class DatasetRead(TimestampedSchema):
    """Dataset summary returned in listings."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    project_id: uuid.UUID
    latest_version: int


class DatasetDetail(DatasetRead):
    """Dataset including its version history."""

    versions: list[DatasetVersionRead] = Field(default_factory=list)
