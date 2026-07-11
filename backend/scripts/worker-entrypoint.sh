#!/usr/bin/env bash
# Container entrypoint for the Celery worker.
#
# The worker waits for the database (the API container owns migrations/seeding),
# then execs the worker command.
set -euo pipefail

echo "[worker-entrypoint] waiting for database..."
python -m app.db.wait_for_db

echo "[worker-entrypoint] starting: $*"
exec "$@"
