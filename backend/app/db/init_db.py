"""Database initialisation entrypoint.

Seeds the RBAC catalog and a bootstrap superuser (idempotently) so a freshly
migrated database is immediately usable. Run as a module — ``python -m
app.db.init_db`` — from the container entrypoint after ``alembic upgrade head``.
Schema creation is owned by Alembic; this script only seeds data.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

# Import the aggregated metadata so *every* model is registered before the ORM
# is used; otherwise string-based relationships (e.g. User -> RefreshToken) fail
# to resolve when the mapper configures.
from app.db import base as _base  # noqa: F401
from app.db.seed import seed_roles, seed_superuser
from app.db.session import AsyncSessionFactory, dispose_engine

logger = get_logger(__name__)


async def init() -> None:
    """Seed roles/permissions and the bootstrap superuser."""
    async with AsyncSessionFactory() as session:
        await seed_roles(session)
        await seed_superuser(
            session,
            email=settings.FIRST_SUPERUSER_EMAIL,
            password=settings.FIRST_SUPERUSER_PASSWORD,
        )
        await session.commit()
    logger.info("database_initialised", superuser=settings.FIRST_SUPERUSER_EMAIL)


async def _main() -> None:
    configure_logging()
    try:
        await init()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
