# Project Status

_Last updated: 2026-07-11_

## Snapshot

| Metric | Value |
|--------|-------|
| Status | **✅ All milestones complete (M1–M9)** |
| Backend tests | 82 passing · ruff / black / mypy clean |
| Frontend tests | 5 passing · typecheck / eslint / build clean |
| Migrations | Initial schema applies & rolls back |
| Docs | MkDocs site builds `--strict` |
| Containers | Backend + frontend Dockerfiles, full compose stack |
| CI | Backend, frontend and docs GitHub Actions |
| Python / Node | 3.12+ / 22+ |
| Runnable | ✅ API boots; frontend renders; suites green |

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

### M5 — EDA & feature engineering
- Automated EDA engine emitting Plotly figure JSON (missing values, histograms,
  box plots, correlation heatmap, scatter of strongest pair, category bars).
- Declarative feature pipeline builder (`ColumnTransformer` + `Pipeline`):
  imputation, one-hot/ordinal encoding, standard/minmax/robust scaling,
  variance/k-best selection, optional PCA.
- EDA + feature-preview endpoints and service; unit + integration tests.

### M6 — AutoML training engine
- `Experiment` + `Run` models; algorithm registry of 11 estimators with graceful
  degradation for optional native libs (XGBoost/LightGBM/CatBoost).
- Training pipeline: preprocessing + estimator, train/test split, Optuna HPO via
  cross-validation, evaluation (classification & regression metrics + ROC /
  confusion-matrix / residual figures), joblib artifact persistence.
- Async execution via Celery (inline mode for tests); best-run selection.
- Explainability: permutation importance (always) + SHAP (tree models).
- Optional, opt-in MLflow tracking.

### M7 — Registry, prediction, notifications, audit
- `Model` registry: promote a run → versioned model; deploy/stage lifecycle
  (single production model per name); list/get/compare/delete.
- Prediction API: JSON records validated against the model's feature schema and
  served through the persisted pipeline (labels + class probabilities).
- Notifications: emitted on experiment completion and model deployment; list,
  unread count, mark-read.
- Audit logs: middleware records every mutating request (actor/action/resource/
  status/ip); admin-only listing.

### M8 — Frontend admin dashboard
- Vite + React 18 + TypeScript (strict) + Tailwind + TanStack Query + React Router
  + React Hook Form.
- Typed Axios client with access-token attach and transparent refresh-token
  rotation interceptor; auth context with protected routes.
- App shell (responsive sidebar/topbar), persisted dark mode, notification bell.
- Pages: Login/Register, Dashboard, Projects, Datasets (upload + statistics),
  Experiments (create + runs + register), Models (deploy + predict).
- Loading/error/empty states throughout; Vitest unit + component tests.
- `npm run build`, `tsc --noEmit`, and `vitest` all pass; verified rendering in
  light and dark themes.

### M9 — DevOps, CI/CD, docs & deployment
- Initial Alembic migration for the full 14-table schema; `ALEMBIC_DATABASE_URL`
  override; DB-readiness waiter, idempotent init/seed CLI, container entrypoints.
- Multi-stage backend Dockerfile (libgomp1 for boosting libs, non-root) and
  frontend Dockerfile (Vite build → Nginx reverse proxy).
- `docker-compose.yml`: Postgres, Redis, MLflow, API, Celery worker, frontend.
- GitHub Actions: backend (ruff/black/mypy/pytest + Postgres migration apply),
  frontend (typecheck/eslint/vitest/build), docs (mkdocs `--strict`).
- MkDocs site: architecture + ER (Mermaid) diagrams, install/deploy/dev/API guides.
- Backend fully lint/format/type-clean; pragmatic mypy config for the ML layer.

### Testing infrastructure
- Test suite runs on a file-backed SQLite database so components that open their
  own session (audit middleware) get an independent connection, mirroring the
  production connection pool.

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
