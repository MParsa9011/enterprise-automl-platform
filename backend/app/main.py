"""Application factory and ASGI entrypoint.

``create_app`` assembles the FastAPI application: logging, middleware (CORS,
security headers, request context, trusted hosts), exception handlers and the
versioned router. Keeping assembly in a factory makes the app trivial to
instantiate with overridden settings in tests, and keeps import-time side
effects out of module scope.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_engine

logger = get_logger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage start-up and shutdown side effects."""
    configure_logging()
    logger.info(
        "application_startup",
        environment=settings.ENVIRONMENT,
        version=__version__,
    )
    yield
    await dispose_engine()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    configure_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=__version__,
        description=(
            "Enterprise AutoML Platform API — dataset management, automated "
            "EDA, feature engineering, AutoML training, explainability and a "
            "model registry with a prediction service."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    _register_middleware(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.PROJECT_NAME,
            "version": __version__,
            "docs": "/docs",
            "api": settings.API_V1_PREFIX,
        }

    return app


def _register_middleware(app: FastAPI) -> None:
    """Register middleware in the correct order (last added runs first)."""
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-Response-Time-ms"],
        )

    if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)


app = create_app()
