"""Block until the database accepts connections.

Used by the container entrypoint before running migrations, so start-up ordering
does not depend solely on compose healthchecks. Retries with exponential backoff
and exits non-zero if the database never becomes reachable.
"""

from __future__ import annotations

import sys

from sqlalchemy import create_engine, text
from tenacity import (
    RetryError,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@retry(stop=stop_after_attempt(30), wait=wait_exponential(multiplier=0.5, max=5))
def _check() -> None:
    """Attempt a single trivial query, raising on failure to trigger a retry."""
    engine = create_engine(settings.sync_database_uri, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()


def main() -> None:
    """Wait for the database, exiting non-zero if it never becomes available."""
    configure_logging()
    try:
        _check()
    except RetryError:
        logger.error("database_unreachable")
        sys.exit(1)
    logger.info("database_ready")


if __name__ == "__main__":
    main()
