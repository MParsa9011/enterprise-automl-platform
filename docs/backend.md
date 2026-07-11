# Backend

The backend is a **FastAPI** application organised with Clean Architecture. This
page is a map of the layers and the key subsystems; see
[Architecture](architecture.md) for the diagrams and [API](api.md) for endpoints.

## Layers

| Package | Responsibility |
|---------|----------------|
| `app/api` | HTTP layer — routers, dependency injection (`deps.py`), middleware, error handlers |
| `app/services` | Business logic (use-cases); the transaction boundary and authorization |
| `app/repositories` | Data access via the Repository pattern (generic `BaseRepository`) |
| `app/models` | SQLAlchemy ORM models |
| `app/schemas` | Pydantic DTOs (request/response contracts) |
| `app/core` | Settings, logging, security, permissions, constants, utilities |
| `app/db` | Async engine/session, declarative base, mixins, seeding, init |
| `app/storage` | Object-storage abstraction (`Storage` interface + `LocalStorage`) |
| `app/ml` | Framework-agnostic ML: io, profiling, EDA, features, algorithms, evaluation, training, explain, tracking |
| `app/worker` | Celery application and training tasks |

## Configuration

All settings live in `app/core/config.py` (`pydantic-settings`). Configuration is
validated at import time, so a misconfigured deployment fails fast. Access it only
via the cached `settings` instance. See `backend/.env.example` for every variable.

## Database & migrations

- **Async SQLAlchemy 2.0** with `asyncpg`; sessions are request-scoped and commit
  on success / roll back on error via the `get_db_session` dependency.
- **Alembic** owns the schema. The initial migration creates all 14 tables.
  Generate new ones with `alembic revision --autogenerate -m "…"`.
- `ALEMBIC_DATABASE_URL` overrides the target DB (handy for autogenerating against
  a throwaway SQLite database when no Postgres is running).
- `app/db/init_db.py` seeds the RBAC catalog and bootstrap superuser (idempotent).

## Security

- **bcrypt** password hashing (guards the 72-byte limit explicitly).
- **JWT** access + refresh tokens; refresh tokens are persisted by `jti` and
  **rotated** on every use (single-use), enabling revocation and logout-everywhere.
- **RBAC** — roles bundle `resource:action` permissions; endpoints are guarded by
  `require_permissions(...)` and services enforce per-instance ownership.

## Asynchronous training

`train_experiment` (Celery) and the inline path both call the same async
`ExperimentService.run_experiment` orchestration. Set `RUN_TRAINING_INLINE=true`
to train in-process without Celery/Redis (used by the test suite).

## The ML engine (`app/ml`)

Pure, synchronous, framework-agnostic modules so they run identically in a request
thread, a Celery worker or a unit test:

- `io.py` — tabular loading + JSON-safe coercion
- `profiling.py` — dataset statistics
- `eda.py` — Plotly EDA figures
- `features.py` — declarative preprocessing pipeline
- `algorithms.py` — algorithm registry (graceful optional-lib degradation)
- `evaluation.py` — metrics + diagnostic figures
- `training.py` — end-to-end train / tune / evaluate / serialise
- `explain.py` — permutation + SHAP importance
- `tracking.py` — optional MLflow logging

## Testing

`pytest` runs on an in-process **SQLite** database (file-backed so independent
sessions — e.g. the audit middleware — work), needing no external services. Markers:
`unit`, `integration`, `ml`. Run `pytest --cov=app`.
