"""JSON Web Token creation and verification.

Two token types are issued:

* **access** — short-lived, sent on every request, carries identity and roles.
* **refresh** — long-lived, exchanged for a new access token; carries a unique
  ``jti`` so individual refresh tokens can be revoked server-side (logout, token
  rotation, credential compromise).

Tokens are signed with HMAC (``HS256`` by default). :func:`decode_token`
validates the signature, expiry and — crucially — the *type*, preventing a
refresh token from being replayed where an access token is expected.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import jwt
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import AuthenticationError


class TokenType(StrEnum):
    """Discriminator embedded in the ``type`` claim of every token."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    """Validated representation of a decoded JWT payload."""

    sub: str = Field(description="Subject — the user id.")
    type: TokenType
    jti: str = Field(description="Unique token identifier.")
    exp: datetime
    iat: datetime
    roles: list[str] = Field(default_factory=list)

    @property
    def user_id(self) -> uuid.UUID:
        """Return the subject parsed as a UUID."""
        return uuid.UUID(self.sub)


class TokenPair(BaseModel):
    """An issued access/refresh token pair returned to clients."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access-token lifetime in seconds.")


def _create_token(
    subject: str | uuid.UUID,
    token_type: TokenType,
    expires_delta: timedelta,
    *,
    roles: list[str] | None = None,
    jti: str | None = None,
) -> tuple[str, str]:
    """Encode a signed JWT; returns ``(token, jti)``."""
    now = datetime.now(UTC)
    token_id = jti or uuid.uuid4().hex
    claims: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type.value,
        "jti": token_id,
        "iat": now,
        "exp": now + expires_delta,
        "roles": roles or [],
    }
    encoded = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, token_id


def create_access_token(
    subject: str | uuid.UUID,
    *,
    roles: list[str] | None = None,
) -> str:
    """Create a short-lived access token for ``subject``."""
    delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token, _ = _create_token(subject, TokenType.ACCESS, delta, roles=roles)
    return token


def create_refresh_token(
    subject: str | uuid.UUID,
    *,
    jti: str | None = None,
) -> tuple[str, str]:
    """Create a long-lived refresh token; returns ``(token, jti)``."""
    delta = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    return _create_token(subject, TokenType.REFRESH, delta, jti=jti)


def create_token_pair(
    subject: str | uuid.UUID,
    *,
    roles: list[str] | None = None,
    refresh_jti: str | None = None,
) -> tuple[TokenPair, str]:
    """Create an access+refresh pair; returns ``(pair, refresh_jti)``."""
    access = create_access_token(subject, roles=roles)
    refresh, jti = create_refresh_token(subject, jti=refresh_jti)
    pair = TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return pair, jti


def decode_token(token: str, *, expected_type: TokenType | None = None) -> TokenPayload:
    """Decode and validate a JWT, enforcing signature, expiry and type.

    Raises :class:`AuthenticationError` for any invalid, expired or
    wrong-type token so callers never have to distinguish JWT library errors.
    """
    try:
        raw = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired.", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Token is invalid.", code="token_invalid") from exc

    payload = TokenPayload.model_validate(raw)
    if expected_type is not None and payload.type != expected_type:
        raise AuthenticationError(
            f"Expected a {expected_type.value} token.", code="token_wrong_type"
        )
    return payload
