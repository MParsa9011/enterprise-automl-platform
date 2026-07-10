"""Async database engine and session management.

Exposes a lazily-constructed async engine, a session factory and the
``get_db_session`` FastAPI dependency. Sessions are scoped to a single request:
the dependency yields a session, commits on success, rolls back on error and
always closes — callers never manage transactions manually for the happy path.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ``pool_pre_ping`` transparently recycles connections dropped by the database
# or an intermediary proxy, which is essential for long-lived pods in k8s.
engine: AsyncEngine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    future=True,
)

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional session per request.

    The session is committed when the request handler returns normally and
    rolled back if any exception propagates, guaranteeing atomicity without the
    handler having to manage the transaction explicitly.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Dispose of the connection pool on application shutdown."""
    await engine.dispose()
