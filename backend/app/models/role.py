"""Role model.

A role is a named bundle of permissions (e.g. ``admin``, ``data_scientist``).
Users acquire capabilities by being assigned roles, never by direct permission
grants, which keeps the authorization model simple to reason about and audit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.associations import role_permissions, user_roles

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.user import User


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named collection of permissions assignable to users."""

    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # System roles are seeded by the platform and cannot be deleted via the API.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
    users: Mapped[list[User]] = relationship(
        secondary=user_roles,
        back_populates="roles",
        lazy="selectin",
    )

    @property
    def permission_names(self) -> set[str]:
        """Return the set of permission names granted by this role."""
        return {permission.name for permission in self.permissions}

    def __repr__(self) -> str:
        return f"<Role {self.name}>"
