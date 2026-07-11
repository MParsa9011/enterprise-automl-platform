"""Authentication endpoints: register, login, refresh, logout and profile."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import (
    AuthServiceDep,
    CurrentUser,
    client_context_from_request,
)
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterResponse,
    TokenResponse,
)
from app.schemas.user import UserCreate, UserRead
from app.services.auth import ClientContext

router = APIRouter(prefix="/auth", tags=["auth"])


def _client(request: Request) -> ClientContext:
    """Build a :class:`ClientContext` from the incoming request."""
    user_agent, ip_address = client_context_from_request(request)
    return ClientContext(user_agent=user_agent, ip_address=ip_address)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
async def register(
    payload: UserCreate,
    service: AuthServiceDep,
    request: Request,
) -> RegisterResponse:
    """Create an account, assign the default role and return the initial tokens."""
    user, tokens = await service.register(payload, client=_client(request))
    return RegisterResponse(
        user=UserRead.model_validate(user),
        tokens=TokenResponse.model_validate(tokens.model_dump()),
    )


@router.post("/login", response_model=TokenResponse, summary="Obtain a token pair")
async def login(
    payload: LoginRequest,
    service: AuthServiceDep,
    request: Request,
) -> TokenResponse:
    """Verify credentials and return an access/refresh token pair."""
    _, tokens = await service.login(payload.email, payload.password, client=_client(request))
    return TokenResponse.model_validate(tokens.model_dump())


@router.post("/refresh", response_model=TokenResponse, summary="Rotate tokens")
async def refresh(
    payload: RefreshRequest,
    service: AuthServiceDep,
    request: Request,
) -> TokenResponse:
    """Exchange a valid refresh token for a new pair, rotating the old one."""
    _, tokens = await service.refresh(payload.refresh_token, client=_client(request))
    return TokenResponse.model_validate(tokens.model_dump())


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
)
async def logout(payload: RefreshRequest, service: AuthServiceDep) -> None:
    """Revoke the presented refresh token (idempotent)."""
    await service.logout(payload.refresh_token)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke all sessions",
)
async def logout_all(current_user: CurrentUser, service: AuthServiceDep) -> None:
    """Revoke every active refresh token for the authenticated user."""
    await service.logout_all(current_user.id)


@router.get("/me", response_model=UserRead, summary="Get the current user")
async def read_me(current_user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile, roles and permissions."""
    return UserRead.model_validate(current_user)
