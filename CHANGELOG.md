# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

## [1.0.0] — 2026-07-11

First public release. A complete, production-grade full-stack AutoML platform.

### Added

**Platform foundation**
- Clean-architecture FastAPI backend (`api → services → repositories → models`)
  with dependency injection, DTOs and a generic async repository.
- Typed settings, structured JSON logging, a domain exception hierarchy with a
  uniform error envelope, and request-id / security-headers / audit middleware.
- Async SQLAlchemy 2.0, Alembic migrations (initial 14-table schema), and
  idempotent RBAC + superuser seeding.

**Authentication & authorization**
- JWT access + refresh tokens with rotation and revocation; bcrypt hashing.
- Role-based access control with fine-grained `resource:action` permissions and
  a declarative permission catalog.

**Datasets & analysis**
- Project workspaces; CSV/Excel/Parquet dataset upload with immutable versioning.
- Automated statistical profiling (types, missingness, IQR outliers, correlations).
- Automated EDA (Plotly figures) and a declarative feature-engineering pipeline
  (imputation, encoding, scaling, selection, PCA).

**AutoML engine**
- Algorithm registry of 11 estimators with graceful degradation for optional
  native libraries (XGBoost / LightGBM / CatBoost).
- Training pipeline with Optuna hyper-parameter optimisation, cross-validation,
  classification/regression evaluation (ROC, confusion matrix, residuals),
  and joblib artifact persistence.
- Asynchronous execution via Celery (with an inline mode for tests).
- Explainability via permutation importance and SHAP; optional MLflow tracking.

**Serving & operations**
- Model registry with versioning, comparison and staged deployment.
- JSON prediction API validating input against the model's feature schema.
- In-app notifications and a structured, append-only audit trail.

**Frontend**
- Vite + React 18 + TypeScript admin dashboard (TailwindCSS, TanStack Query,
  React Router, React Hook Form) with a typed API client and transparent
  refresh-token rotation.
- Responsive app shell, persisted dark mode, notification bell, and pages for
  auth, dashboard, projects, datasets, experiments and the model registry.

**DevOps & docs**
- Multi-stage backend and frontend Dockerfiles; full `docker-compose` stack
  (Postgres, Redis, MLflow, API, worker, Nginx) plus a hardened production override.
- GitHub Actions CI for backend (ruff/black/mypy/pytest + Postgres migration),
  frontend (typecheck/eslint/vitest/build) and docs (MkDocs strict).
- MkDocs documentation with architecture and ER diagrams, plus community health
  files (Code of Conduct, Security, Support, issue/PR templates).

### Notes

- 84 backend tests and frontend unit/component tests pass; the full flow was
  verified end-to-end against a live PostgreSQL database.

[Unreleased]: https://github.com/MParsa9011/enterprise-automl-platform/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/MParsa9011/enterprise-automl-platform/releases/tag/v1.0.0
