"""Optional MLflow experiment tracking.

Logging is entirely best-effort and opt-in (``MLFLOW_ENABLED``): if the library
is missing or the tracking server is unreachable, training proceeds unaffected.
This lets the platform integrate with MLflow in environments that provide it
(the Docker stack) while the DB-backed ``Experiment``/``Run`` records remain the
authoritative store everywhere.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def log_run(
    *,
    experiment_name: str,
    run_name: str,
    algorithm: str,
    params: dict[str, Any],
    metrics: dict[str, float],
) -> None:
    """Log a training run to MLflow when enabled; silently no-op otherwise."""
    if not settings.MLFLOW_ENABLED:
        return
    try:
        import mlflow

        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name):
            mlflow.log_param("algorithm", algorithm)
            mlflow.log_params({k: v for k, v in params.items() if _is_scalar(v)})
            mlflow.log_metrics({k: float(v) for k, v in metrics.items() if _is_number(v)})
    except Exception as exc:
        logger.info("mlflow_logging_skipped", error=str(exc))


def _is_scalar(value: Any) -> bool:
    return isinstance(value, str | int | float | bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
