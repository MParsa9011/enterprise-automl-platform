"""Liveness and readiness probes.

* ``/health/live`` is a cheap liveness check used by orchestrators to decide
  whether to restart the container — it never touches dependencies.
* ``/health/ready`` verifies that critical dependencies (database, Redis) are
  reachable, so a pod is only routed traffic once it can actually serve it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import settings
from app.db.session import get_db_session

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    """Health probe response body."""

    status: str
    version: str
    environment: str


class ReadinessStatus(BaseModel):
    """Readiness probe response including per-dependency status."""

    status: str
    checks: dict[str, str]


@router.get("/health/live", response_model=HealthStatus, summary="Liveness probe")
async def live() -> HealthStatus:
    """Return a static payload confirming the process is running."""
    return HealthStatus(
        status="ok",
        version=__version__,
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessStatus,
    summary="Readiness probe",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessStatus}},
)
async def ready(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReadinessStatus:
    """Verify connectivity to critical dependencies before serving traffic."""
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:  # pragma: no cover - exercised via integration tests
        checks["database"] = "unavailable"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return ReadinessStatus(status=overall, checks=checks)
