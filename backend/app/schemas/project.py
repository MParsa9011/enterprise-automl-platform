"""Project data-transfer objects."""

from __future__ import annotations

import uuid

from pydantic import Field

from app.schemas.base import Schema, TimestampedSchema
from app.schemas.user import UserSummary


class ProjectCreate(Schema):
    """Payload for creating a project."""

    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class ProjectUpdate(Schema):
    """Partial update payload for a project."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class ProjectRead(TimestampedSchema):
    """Project representation returned to clients."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    owner_id: uuid.UUID
    owner: UserSummary
