"""Shared FastAPI dependencies (composition root).

This module is where the object graph is wired together: sessions produce
repositories, repositories produce services, and services are injected into
endpoints. Centralising construction here keeps endpoints declarative and makes
every collaborator overridable in tests via ``app.dependency_overrides``.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import TokenType, decode_token
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import RoleRepository, UserRepository
from app.services.auth import AuthService
from app.services.project import ProjectService

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

# ``auto_error=False`` lets us raise our own domain error (rendered as the
# standard envelope) instead of Starlette's default 403 body.
_bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]


# ---------------------------------------------------------------------------
# Repository providers
# ---------------------------------------------------------------------------
def get_user_repository(db: DbSession) -> UserRepository:
    """Provide a :class:`UserRepository` bound to the request session."""
    return UserRepository(db)


def get_role_repository(db: DbSession) -> RoleRepository:
    """Provide a :class:`RoleRepository` bound to the request session."""
    return RoleRepository(db)


def get_refresh_token_repository(db: DbSession) -> RefreshTokenRepository:
    """Provide a :class:`RefreshTokenRepository` bound to the request session."""
    return RefreshTokenRepository(db)


def get_project_repository(db: DbSession) -> ProjectRepository:
    """Provide a :class:`ProjectRepository` bound to the request session."""
    return ProjectRepository(db)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
RoleRepo = Annotated[RoleRepository, Depends(get_role_repository)]
RefreshTokenRepo = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)]
ProjectRepo = Annotated[ProjectRepository, Depends(get_project_repository)]


# ---------------------------------------------------------------------------
# Service providers
# ---------------------------------------------------------------------------
def get_auth_service(
    users: UserRepo,
    roles: RoleRepo,
    refresh_tokens: RefreshTokenRepo,
) -> AuthService:
    """Provide a fully-wired :class:`AuthService`."""
    return AuthService(users=users, roles=roles, refresh_tokens=refresh_tokens)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_project_service(projects: ProjectRepo) -> ProjectService:
    """Provide a :class:`ProjectService`."""
    return ProjectService(projects)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


# ---------------------------------------------------------------------------
# Authentication / authorization
# ---------------------------------------------------------------------------
async def get_current_user(credentials: BearerToken, users: UserRepo) -> User:
    """Resolve and return the authenticated user from a bearer access token."""
    if credentials is None:
        raise AuthenticationError("Not authenticated.", code="not_authenticated")

    payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    user = await users.get(payload.user_id)
    if user is None:
        raise AuthenticationError("User no longer exists.", code="user_not_found")
    if not user.is_active:
        raise AuthenticationError("This account is disabled.", code="account_disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_active_superuser(current_user: CurrentUser) -> User:
    """Require the authenticated user to be a superuser."""
    if not current_user.is_superuser:
        raise PermissionDeniedError("Superuser privileges are required.")
    return current_user


CurrentSuperuser = Annotated[User, Depends(get_current_active_superuser)]

_Guard = Callable[[User], Coroutine[Any, Any, User]]


def require_roles(*roles: str) -> _Guard:
    """Build a dependency asserting the user holds *any* of the given roles."""
    required = set(roles)

    async def _guard(current_user: CurrentUser) -> User:
        if current_user.is_superuser or required & current_user.role_names:
            return current_user
        raise PermissionDeniedError(
            "You do not have the required role for this action.",
            details={"required_roles": sorted(required)},
        )

    return _guard


def require_permissions(*permissions: str) -> _Guard:
    """Build a dependency asserting the user holds *all* given permissions."""
    required = set(permissions)

    async def _guard(current_user: CurrentUser) -> User:
        if current_user.is_superuser or required <= current_user.permissions:
            return current_user
        missing = sorted(required - current_user.permissions)
        raise PermissionDeniedError(
            "You do not have the required permissions for this action.",
            details={"missing_permissions": missing},
        )

    return _guard


def client_context_from_request(request: Request) -> tuple[str | None, str | None]:
    """Extract a (user_agent, client_ip) tuple from the incoming request."""
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    return user_agent, client_ip
