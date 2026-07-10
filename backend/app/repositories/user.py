"""User and role data-access repositories."""

from __future__ import annotations

from sqlalchemy import select

from app.models.role import Role
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Persistence operations for :class:`User`."""

    model = User
    searchable_fields = ("email", "full_name")

    async def get_by_email(self, email: str) -> User | None:
        """Return the user with the given email (case-insensitive), or ``None``."""
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Return whether a user already exists with the given email."""
        stmt = select(User.id).where(User.email == email.lower()).limit(1)
        result = await self.session.execute(stmt)
        return result.first() is not None


class RoleRepository(BaseRepository[Role]):
    """Persistence operations for :class:`Role`."""

    model = Role
    searchable_fields = ("name", "description")

    async def get_by_name(self, name: str) -> Role | None:
        """Return the role with the given name, or ``None``."""
        stmt = select(Role).where(Role.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_names(self, names: list[str]) -> list[Role]:
        """Return all roles whose names are in ``names``."""
        if not names:
            return []
        stmt = select(Role).where(Role.name.in_(names))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
