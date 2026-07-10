"""Authentication use-cases.

Encapsulates registration, credential verification, token issuance and the
refresh-token lifecycle (rotation and revocation). The service depends only on
repository abstractions and the stateless security helpers, so its logic can be
unit-tested without a running web server.

Security notes:

* Login failures return a single, generic error regardless of whether the email
  exists, to avoid user enumeration.
* Refresh tokens are *rotated*: each successful refresh revokes the presented
  token and issues a brand-new pair, so a leaked refresh token is usable at most
  once before detection.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.constants import Role as RoleName
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.logging import get_logger
from app.core.security import (
    TokenPair,
    TokenType,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import RoleRepository, UserRepository
from app.schemas.user import UserCreate

logger = get_logger(__name__)


@dataclass(slots=True, frozen=True)
class ClientContext:
    """Lightweight client fingerprint captured for issued sessions."""

    user_agent: str | None = None
    ip_address: str | None = None


class AuthService:
    """Application service implementing authentication use-cases."""

    def __init__(
        self,
        users: UserRepository,
        roles: RoleRepository,
        refresh_tokens: RefreshTokenRepository,
    ) -> None:
        self._users = users
        self._roles = roles
        self._refresh_tokens = refresh_tokens

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    async def register(
        self,
        data: UserCreate,
        *,
        client: ClientContext | None = None,
    ) -> tuple[User, TokenPair]:
        """Create a new user, assign the default role and issue a token pair."""
        email = data.email.lower()
        if await self._users.email_exists(email):
            raise ConflictError("An account with this email already exists.")

        user = User(
            email=email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            is_active=True,
        )
        default_role = await self._roles.get_by_name(RoleName.VIEWER)
        if default_role is not None:
            user.roles.append(default_role)

        user = await self._users.add(user)
        logger.info("user_registered", user_id=str(user.id), email=email)

        pair = await self._issue_pair(user, client)
        return user, pair

    # ------------------------------------------------------------------
    # Login / credential verification
    # ------------------------------------------------------------------
    async def authenticate(self, email: str, password: str) -> User:
        """Verify credentials and return the user, or raise on failure."""
        user = await self._users.get_by_email(email.lower())
        # Verify against a real-or-dummy hash either way to keep timing uniform.
        candidate_hash = user.hashed_password if user else _DUMMY_HASH
        password_ok = verify_password(password, candidate_hash)

        if user is None or not password_ok:
            raise AuthenticationError("Incorrect email or password.")
        if not user.is_active:
            raise AuthenticationError("This account is disabled.", code="account_disabled")
        return user

    async def login(
        self,
        email: str,
        password: str,
        *,
        client: ClientContext | None = None,
    ) -> tuple[User, TokenPair]:
        """Authenticate a user and issue a fresh token pair."""
        user = await self.authenticate(email, password)
        user.last_login_at = datetime.now(UTC)
        await self._users.add(user)
        pair = await self._issue_pair(user, client)
        logger.info("user_login", user_id=str(user.id))
        return user, pair

    # ------------------------------------------------------------------
    # Refresh / rotation
    # ------------------------------------------------------------------
    async def refresh(
        self,
        refresh_token: str,
        *,
        client: ClientContext | None = None,
    ) -> tuple[User, TokenPair]:
        """Exchange a valid refresh token for a new pair, rotating the old one."""
        payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
        record = await self._refresh_tokens.get_by_jti(payload.jti)

        if record is None or not record.is_active:
            # Reuse of a rotated/revoked token is a strong compromise signal:
            # defensively revoke every session for the subject.
            await self._refresh_tokens.revoke_all_for_user(payload.user_id)
            raise AuthenticationError(
                "Refresh token is no longer valid.", code="refresh_invalid"
            )

        user = await self._users.get(payload.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Account is unavailable.", code="account_disabled")

        await self._refresh_tokens.revoke(record)
        pair = await self._issue_pair(user, client)
        logger.info("token_refreshed", user_id=str(user.id))
        return user, pair

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------
    async def logout(self, refresh_token: str) -> None:
        """Revoke a single refresh token (best-effort; never leaks validity)."""
        try:
            payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
        except AuthenticationError:
            return
        record = await self._refresh_tokens.get_by_jti(payload.jti)
        if record is not None:
            await self._refresh_tokens.revoke(record)

    async def logout_all(self, user_id: uuid.UUID) -> int:
        """Revoke all of a user's refresh tokens; returns the count revoked."""
        revoked = await self._refresh_tokens.revoke_all_for_user(user_id)
        logger.info("logout_all", user_id=str(user_id), revoked=revoked)
        return revoked

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _issue_pair(self, user: User, client: ClientContext | None) -> TokenPair:
        """Issue a token pair and persist the refresh token for revocation."""
        pair, jti = create_token_pair(user.id, roles=sorted(user.role_names))
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
        record = RefreshToken(
            jti=jti,
            user_id=user.id,
            expires_at=expires_at,
            user_agent=(client.user_agent if client else None),
            ip_address=(client.ip_address if client else None),
        )
        await self._refresh_tokens.add(record)
        return pair


# Pre-computed bcrypt hash of a random string, used to equalise timing between
# "user not found" and "wrong password" paths (mitigates user enumeration).
_DUMMY_HASH = hash_password(uuid.uuid4().hex)
