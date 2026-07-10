"""Project-wide constants and enumerations shared across layers."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Built-in role names for role-based access control."""

    ADMIN = "admin"
    MANAGER = "manager"
    DATA_SCIENTIST = "data_scientist"
    VIEWER = "viewer"


class TaskType(StrEnum):
    """Supported supervised/unsupervised learning task types."""

    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"


class DatasetFileType(StrEnum):
    """Accepted dataset source formats."""

    CSV = "csv"
    EXCEL = "excel"
    PARQUET = "parquet"


class ExperimentStatus(StrEnum):
    """Lifecycle states of an AutoML experiment."""

    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunStatus(StrEnum):
    """Lifecycle states of an individual training run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelStage(StrEnum):
    """Model registry promotion stages, mirroring MLflow semantics."""

    NONE = "none"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class NotificationType(StrEnum):
    """Categories of user-facing notifications."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


# HTTP header carrying the per-request correlation id.
REQUEST_ID_HEADER = "X-Request-ID"
