"""Project (workspace) model.

A project is the top-level container that owns datasets, experiments and models.
It belongs to a single owner and can later be shared with collaborators. Projects
are soft-deleted so that dependent artifacts and audit history remain intact and
recoverable after a deletion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Project(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A workspace owned by a user that groups ML artifacts."""

    __table_args__ = (
        # A given owner cannot have two live projects with the same slug.
        UniqueConstraint("owner_id", "slug", name="uq_projects_owner_id_slug"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    owner: Mapped["User"] = relationship(lazy="joined")

    def __repr__(self) -> str:
        return f"<Project {self.slug} owner={self.owner_id}>"
