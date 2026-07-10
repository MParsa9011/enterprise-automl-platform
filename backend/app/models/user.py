"""User model.

Represents an authenticated principal. Authorization data (roles/permissions) is
loaded eagerly via ``selectin`` so a fully-populated user can be attached to the
request context in a single query graph, avoiding N+1 lookups when checking
permissions on hot paths.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.associations import user_roles

if TYPE_CHECKING:
    from app.models.refresh_token import RefreshToken
    from app.models.role import Role


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A registered platform user."""

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Superusers bypass permission checks entirely (break-glass / platform ops).
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------
    @property
    def role_names(self) -> set[str]:
        """Names of every role assigned to the user."""
        return {role.name for role in self.roles}

    @property
    def permissions(self) -> set[str]:
        """Flattened set of permission names granted across all roles."""
        return {name for role in self.roles for name in role.permission_names}

    def has_role(self, role: str) -> bool:
        """Return whether the user holds the named role."""
        return role in self.role_names

    def has_permission(self, permission: str) -> bool:
        """Return whether the user is granted a permission (superusers: always)."""
        return self.is_superuser or permission in self.permissions

    def __repr__(self) -> str:
        return f"<User {self.email}>"
