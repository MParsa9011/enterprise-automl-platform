"""Base schema classes shared by all DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    """Base class for request/response DTOs.

    ``from_attributes`` lets response models be constructed directly from ORM
    instances, and ``populate_by_name`` allows both field names and aliases.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )


class TimestampedSchema(Schema):
    """Mixin adding the standard audit timestamps to response DTOs."""

    created_at: datetime
    updated_at: datetime


# Reusable constrained field types.
NonEmptyStr = Annotated[str, Field(min_length=1, max_length=255)]
DescriptionStr = Annotated[str | None, Field(default=None, max_length=2000)]
