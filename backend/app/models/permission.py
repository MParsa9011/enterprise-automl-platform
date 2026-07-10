"""Permission model.

A permission is a fine-grained capability expressed as ``resource:action``
(e.g. ``project:create``, ``model:deploy``). Permissions are grouped into roles;
users are granted roles. This indirection keeps authorization declarative and
lets new roles be composed without touching application code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.associations import role_permissions

if TYPE_CHECKING:
    from app.models.role import Role


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single, atomic authorization capability."""

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.name}>"
