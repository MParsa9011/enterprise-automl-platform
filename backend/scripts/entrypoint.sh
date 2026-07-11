#!/usr/bin/env bash
# Container entrypoint for the API service.
#
# Waits for the database, applies migrations, seeds baseline data, then execs the
# provided command (e.g. gunicorn). Migrations/seeding are idempotent, so running
# this on every container start is safe.
set -euo pipefail

echo "[entrypoint] waiting for database..."
python -m app.db.wait_for_db

echo "[entrypoint] applying migrations..."
alembic upgrade head

echo "[entrypoint] seeding baseline data..."
python -m app.db.init_db

echo "[entrypoint] starting: $*"
exec "$@"
