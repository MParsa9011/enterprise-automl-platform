"""Shared pytest fixtures.

Every test runs against a fresh in-memory SQLite database created from the ORM
metadata, so the suite is fast, hermetic and requires no external services. A
``StaticPool`` keeps the single in-memory connection alive across sessions so the
test client and helper fixtures observe the same data. The application's
``get_db_session`` dependency is overridden to use this database.
"""

from __future__ import annotations

import os

# Train experiments inline (no Celery/Redis) during tests. Must be set before the
# application settings are imported below so the cached Settings picks it up.
os.environ.setdefault("RUN_TRAINING_INLINE", "true")

import uuid  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_storage
from app.db.base import Base
from app.db.seed import seed_roles, seed_superuser
from app.db.session import get_db_session
from app.main import create_app
from app.storage import LocalStorage

TEST_SUPERUSER_EMAIL = "admin@example.com"
TEST_SUPERUSER_PASSWORD = "Admin12345!"


@pytest_asyncio.fixture
async def engine(tmp_path_factory: pytest.TempPathFactory) -> AsyncGenerator[AsyncEngine, None]:
    """Provide a file-backed SQLite engine with the full schema created.

    A temporary *file* (not ``:memory:``) is used so that components which open
    their own session — notably the audit middleware — get an independent
    connection to the same database, mirroring production's connection pool.
    """
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Provide a session factory bound to the test engine."""
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a session for direct data setup/assertions inside tests."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def seeded(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Seed default RBAC roles/permissions before a test runs."""
    async with session_factory() as session:
        await seed_roles(session)
        await session.commit()


@pytest_asyncio.fixture
async def client(
    engine: AsyncEngine,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path_factory: pytest.TempPathFactory,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx client wired to the app with test DB and storage."""
    app = create_app()
    storage_root = tmp_path_factory.mktemp("storage")

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_get_db
    app.dependency_overrides[get_storage] = lambda: LocalStorage(storage_root)
    # Point session-less components (audit middleware) at the test database.
    app.state.session_factory = session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def superuser(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, str]:
    """Seed a superuser and return its credentials."""
    async with session_factory() as session:
        await seed_superuser(
            session,
            email=TEST_SUPERUSER_EMAIL,
            password=TEST_SUPERUSER_PASSWORD,
        )
        await session.commit()
    return {"email": TEST_SUPERUSER_EMAIL, "password": TEST_SUPERUSER_PASSWORD}


@pytest.fixture
def unique_email() -> str:
    """Return a unique email address for registration tests."""
    return f"user-{uuid.uuid4().hex[:12]}@example.com"
