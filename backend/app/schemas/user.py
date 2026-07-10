"""User and RBAC data-transfer objects."""

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import EmailStr, Field, field_validator

from app.core.config import settings
from app.schemas.base import Schema, TimestampedSchema

# bcrypt cannot hash more than 72 bytes; reject longer passwords up front.
PasswordStr = Annotated[str, Field(min_length=settings.PASSWORD_MIN_LENGTH, max_length=72)]


class PermissionRead(Schema):
    """Serialised permission."""

    id: uuid.UUID
    name: str
    resource: str
    action: str
    description: str | None = None


class RoleRead(Schema):
    """Serialised role including its permissions."""

    id: uuid.UUID
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[PermissionRead] = Field(default_factory=list)


class UserBase(Schema):
    """Fields common to user input DTOs."""

    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    """Registration payload."""

    password: PasswordStr

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        """Require a mix of letters and digits for a minimal strength floor."""
        if value.isalpha() or value.isdigit():
            raise ValueError("Password must contain both letters and numbers.")
        return value


class UserUpdate(Schema):
    """Partial update payload for a user's own profile."""

    full_name: str | None = Field(default=None, max_length=255)
    password: PasswordStr | None = None


class UserAdminUpdate(UserUpdate):
    """Administrative update allowing activation and role changes."""

    is_active: bool | None = None
    is_verified: bool | None = None
    role_names: list[str] | None = None


class UserRead(TimestampedSchema):
    """User representation returned to clients."""

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_superuser: bool
    is_verified: bool
    roles: list[RoleRead] = Field(default_factory=list)


class UserSummary(Schema):
    """Compact user representation for embedding in other resources."""

    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
