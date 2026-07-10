"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
using :mod:`pydantic-settings`. A single cached :class:`Settings` instance is
exposed through :func:`get_settings`, which is the only supported way to access
configuration throughout the application. This keeps configuration a single
source of truth and makes it trivially overridable in tests.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    PostgresDsn,
    RedisDsn,
    ValidationInfo,
    computed_field,
    field_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "development", "staging", "production", "test"]


def _split_csv(value: Any) -> Any:
    """Allow list-typed settings to be provided as a comma-separated string."""
    if isinstance(value, str) and not value.startswith("["):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Every value is validated at import time, so a misconfigured deployment fails
    fast and loudly rather than at the first request that touches the bad value.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=True,
        extra="ignore",
    )

    # --- General ---------------------------------------------------------
    PROJECT_NAME: str = "Enterprise AutoML Platform"
    ENVIRONMENT: Environment = "local"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    VERSION: str = "0.1.0"

    # --- Security --------------------------------------------------------
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(64))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14  # 14 days
    JWT_ALGORITHM: str = "HS256"
    PASSWORD_MIN_LENGTH: int = 8
    # Role granted to self-registered users. On a self-serve ML platform this is
    # a builder role so new users can create their own workspace; read-only
    # collaborators are assigned the "viewer" role by an administrator.
    DEFAULT_USER_ROLE: str = "data_scientist"

    # --- CORS ------------------------------------------------------------
    # ``NoDecode`` disables pydantic-settings' implicit JSON decoding so the
    # ``_split_csv`` validator can accept a plain comma-separated string.
    BACKEND_CORS_ORIGINS: Annotated[list[AnyHttpUrl], NoDecode, Field(default_factory=list)]
    ALLOWED_HOSTS: Annotated[list[str], NoDecode, Field(default_factory=lambda: ["*"])]

    # --- Database --------------------------------------------------------
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "automl"
    POSTGRES_PASSWORD: str = "automl"
    POSTGRES_DB: str = "automl"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False
    SQLALCHEMY_DATABASE_URI: PostgresDsn | None = None

    # --- Redis / Celery --------------------------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: RedisDsn | None = None
    CELERY_RESULT_BACKEND: RedisDsn | None = None

    # --- Rate limiting ---------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 120

    # --- Storage / ML ----------------------------------------------------
    STORAGE_ROOT: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 512
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # --- Pagination ------------------------------------------------------
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # --- Logging ---------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    _split_cors = field_validator("BACKEND_CORS_ORIGINS", mode="before")(_split_csv)
    _split_hosts = field_validator("ALLOWED_HOSTS", mode="before")(_split_csv)

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def _assemble_db_uri(cls, value: Any, info: ValidationInfo) -> Any:
        """Build the async Postgres DSN from parts when not explicitly set."""
        if isinstance(value, str) and value:
            return value
        data = info.data
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=data.get("POSTGRES_USER"),
            password=data.get("POSTGRES_PASSWORD"),
            host=data.get("POSTGRES_SERVER"),
            port=data.get("POSTGRES_PORT"),
            path=data.get("POSTGRES_DB"),
        )

    @field_validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def _assemble_redis_uri(cls, value: Any, info: ValidationInfo) -> Any:
        """Default Celery broker/backend to the configured Redis instance."""
        if isinstance(value, str) and value:
            return value
        data = info.data
        return RedisDsn.build(
            scheme="redis",
            host=data.get("REDIS_HOST", "localhost"),
            port=data.get("REDIS_PORT", 6379),
            path=str(data.get("REDIS_DB", 0)),
        )

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """True when running in a production-like environment."""
        return self.ENVIRONMENT in ("staging", "production")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_uri(self) -> str:
        """Synchronous DSN (psycopg) used by Alembic migrations."""
        uri = str(self.SQLALCHEMY_DATABASE_URI)
        return uri.replace("postgresql+asyncpg", "postgresql+psycopg")

    @property
    def cors_origins(self) -> list[str]:
        """CORS origins as plain strings for Starlette middleware."""
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]


@lru_cache
def get_settings() -> Settings:
    """Return the cached, process-wide settings instance."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
