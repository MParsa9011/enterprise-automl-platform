"""Structured logging configuration.

The application uses :mod:`structlog` layered on top of the standard library
``logging`` so that:

* Application code and third-party libraries share a single output stream.
* Every log line carries contextual key/value pairs (request id, user id, ...).
* Output is machine-readable JSON in production and human-friendly in local dev.

Call :func:`configure_logging` exactly once during application start-up.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.core.config import settings

# Marks the handler this module installs so re-configuration can replace it
# without disturbing handlers owned by other frameworks (e.g. pytest).
_APP_HANDLER_MARKER = "_automl_app_handler"


def _shared_processors() -> list[Processor]:
    """Processors applied to both structlog and stdlib log records."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


def configure_logging() -> None:
    """Configure structlog and the standard logging module.

    Idempotent: safe to call more than once (e.g. in tests) without stacking
    handlers.
    """
    shared = _shared_processors()

    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if settings.LOG_JSON
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    setattr(handler, _APP_HANDLER_MARKER, True)

    root = logging.getLogger()
    # Remove only *our* previously-installed handler so re-configuring is
    # idempotent, while preserving foreign handlers (e.g. pytest's log capture).
    for existing in list(root.handlers):
        if getattr(existing, _APP_HANDLER_MARKER, False):
            root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL.upper())

    # Tame noisy third-party loggers.
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "aiosqlite"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Route uvicorn error logs through our handler for consistent formatting.
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True


def get_logger(name: str | None = None, **initial: Any) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger, optionally pre-bound with context."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    if initial:
        logger = logger.bind(**initial)
    return logger
