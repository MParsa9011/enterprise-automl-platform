"""Idempotent seeding of RBAC data and the bootstrap superuser.

Seeding is idempotent: it inserts only what is missing and reconciles role→
permission grants on every run, so it is safe to execute on every deployment
(e.g. from an init container or a management command). This keeps the
authorization catalog in :mod:`app.core.permissions` and the database in sync.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.permissions import PERMISSIONS, ROLES
from app.core.security import hash_password
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

logger = get_logger(__name__)


async def seed_permissions(session: AsyncSession) -> dict[str, Permission]:
    """Ensure every catalog permission exists; return a name→row mapping."""
    existing = {p.name: p for p in (await session.execute(select(Permission))).scalars()}
    for spec in PERMISSIONS:
        if spec.name not in existing:
            permission = Permission(
                name=spec.name,
                resource=spec.resource,
                action=spec.action,
                description=spec.description,
            )
            session.add(permission)
            existing[spec.name] = permission
    await session.flush()
    return existing


async def seed_roles(session: AsyncSession) -> dict[str, Role]:
    """Ensure catalog roles exist and their permission grants are reconciled."""
    permissions = await seed_permissions(session)
    existing = {r.name: r for r in (await session.execute(select(Role))).scalars()}

    for spec in ROLES:
        role = existing.get(spec.name)
        if role is None:
            role = Role(name=spec.name, description=spec.description, is_system=spec.is_system)
            session.add(role)
            existing[spec.name] = role
        # Reconcile grants so catalog changes propagate on the next seed.
        role.permissions = [permissions[name] for name in sorted(spec.permissions)]
    await session.flush()
    logger.info("rbac_seeded", roles=len(ROLES), permissions=len(PERMISSIONS))
    return existing


async def seed_superuser(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str = "Platform Administrator",
) -> User:
    """Create (or return) the bootstrap superuser, granting the admin role."""
    from app.core.constants import Role as RoleName

    result = await session.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    roles = await seed_roles(session)
    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
        is_active=True,
        is_superuser=True,
        is_verified=True,
    )
    if (admin := roles.get(RoleName.ADMIN)) is not None:
        user.roles.append(admin)
    session.add(user)
    await session.flush()
    logger.info("superuser_seeded", email=email)
    return user
