# Project Status

_Last updated: 2026-07-11_

## Snapshot

| Metric | Value |
|--------|-------|
| Current milestone | **M5 — EDA & feature engineering** (starting) |
| Completed milestones | M1–M4 |
| Backend tests | 47 passing |
| Python | 3.12+ (dev venv on 3.13) |
| Runnable | ✅ API boots; test suite green |

## Completed

### M1 — Foundation
- Typed settings (`pydantic-settings`), structured JSON logging (`structlog`).
- Domain exception hierarchy + centralised handlers with a uniform error envelope.
- Async SQLAlchemy 2.0 engine/session, declarative base with naming conventions,
  UUID/timestamp/soft-delete mixins.
- Generic async repository (pagination, filtering, sorting, search, soft-delete hook).
- App factory, request-context + security-headers middleware, health/readiness probes.
- Alembic scaffolding, developer `Makefile`.

### M2 — Auth & RBAC
- `User`, `Role`, `Permission`, `RefreshToken` models.
- bcrypt password hashing; JWT access + refresh tokens with rotation & revocation.
- RBAC permission catalog + idempotent seeding; superuser bootstrap.
- Endpoints: register, login, refresh, logout, logout-all, me.
- Role/permission guard dependencies.

### M3 — Projects
- `Project` model (owner-scoped, soft-deletable, unique slug per owner).
- Ownership-aware service; CRUD endpoints with permission guards; pagination.

### M4 — Datasets
- `Dataset` + immutable `DatasetVersion` models.
- Storage abstraction (`Storage` interface + `LocalStorage` backend).
- CSV/Excel/Parquet loading; full statistical profiling engine (type inference,
  missingness, outliers (IQR), numeric/categorical summaries, correlations).
- Upload/versioning/statistics/download endpoints.

## Architecture notes
- Clean Architecture: `api → services → repositories → models`, with `schemas`
  (DTOs), `storage` and `ml` as supporting layers.
- Dependency injection via FastAPI `Depends`; composition root in `app/api/deps.py`.
- ML logic (`app/ml`) is framework-agnostic and reusable from Celery workers.

## Known gaps / deferred
- Alembic migration files are generated in **M9** against Postgres (tests use
  `create_all` on SQLite). App is runnable against the ORM today.
- Docker/compose, CI, and MkDocs land in **M9**.

See [NEXT_TASK.md](NEXT_TASK.md) for the immediate next step and [ROADMAP.md](ROADMAP.md)
for the full plan.
