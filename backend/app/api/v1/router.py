"""Aggregate router for API v1.

Feature routers are included here as they are implemented, keeping
``main.py`` free of endpoint wiring. A single ``api_router`` is mounted under the
configured version prefix by the application factory.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, projects

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(projects.router)
