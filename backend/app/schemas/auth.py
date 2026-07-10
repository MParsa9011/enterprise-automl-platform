"""Authentication request/response DTOs."""

from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas.base import Schema
from app.schemas.user import UserRead


class LoginRequest(Schema):
    """Credential payload for the login endpoint."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(Schema):
    """Payload carrying a refresh token to be exchanged for a new pair."""

    refresh_token: str = Field(min_length=1)


class TokenResponse(Schema):
    """Access/refresh token pair returned on login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access-token lifetime in seconds.")


class RegisterResponse(Schema):
    """Response returned after a successful registration."""

    user: UserRead
    tokens: TokenResponse
