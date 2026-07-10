"""Refresh-token model.

Every issued refresh token is persisted so it can be revoked independently of its
cryptographic expiry. This underpins secure logout, refresh-token *rotation*
(each use invalidates the previous token and issues a new one) and bulk
revocation on password change or suspected compromise. Only the token's ``jti``
is stored — never the token string itself — so a database leak cannot be used to
mint sessions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A persisted, revocable refresh-token record."""

    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Lightweight client fingerprint for the "active sessions" view / audit.
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    @property
    def is_revoked(self) -> bool:
        """Whether the token has been explicitly revoked."""
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """Whether the token has passed its expiry timestamp."""
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return datetime.now(UTC) >= expires

    @property
    def is_active(self) -> bool:
        """Whether the token is currently usable (not revoked, not expired)."""
        return not self.is_revoked and not self.is_expired

    def __repr__(self) -> str:
        return f"<RefreshToken jti={self.jti} user_id={self.user_id}>"
