"""Refresh-token data-access repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Persistence operations for :class:`RefreshToken`."""

    model = RefreshToken

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        """Return the token record with the given ``jti``, or ``None``."""
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        """Mark a single token record as revoked (idempotent)."""
        if token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)
            self.session.add(token)
            await self.session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke every active token for a user; returns the count revoked.

        Used on logout-everywhere, password change and suspected compromise.
        """
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        # rowcount is present on the CursorResult returned by UPDATE/DELETE, but
        # SQLAlchemy types execute() as the base Result which omits it.
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
