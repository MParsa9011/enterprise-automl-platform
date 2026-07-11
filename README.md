<div align="center">

# 🤖 Enterprise AutoML Platform

**A production-grade platform for automated machine learning** — upload data,
run automated EDA and feature engineering, train and tune dozens of models,
explain them, and serve predictions through a versioned model registry.

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=github-actions&logoColor=white)](.github/workflows)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](backend/pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

The Enterprise AutoML Platform lets data teams go from a raw CSV to a deployed,
explainable model without writing training code. It is built as a modular,
horizontally-scalable system with a clean separation between the API, business
logic, data access and the ML engine.

> **Status:** actively built in vertical slices — see [PROJECT_STATUS.md](PROJECT_STATUS.md)
> and [ROADMAP.md](ROADMAP.md). Backend M1–M4 are complete with 47 passing tests.

## Key features

- 🔐 **Auth & RBAC** — JWT access/refresh tokens with rotation & revocation, roles
  and fine-grained permissions.
- 🗂️ **Workspaces** — projects that own datasets, experiments and models.
- 📊 **Dataset management** — CSV/Excel/Parquet upload, immutable versioning, and
  automated statistical profiling (types, missingness, outliers, correlations).
- 🔎 **Automated EDA** — distributions, box/scatter plots and correlation heatmaps.
- 🧪 **Feature engineering** — imputation, encoding, scaling, selection and PCA.
- ⚙️ **AutoML** — 11 algorithms across classification/regression/clustering with
  Optuna hyper-parameter optimisation, tracked in MLflow.
- 🧠 **Explainability** — SHAP, permutation importance and partial dependence.
- 📦 **Model registry** — versioning, comparison, staged deployment.
- 🚀 **Prediction API** — send JSON, receive predictions from deployed models.

## Tech stack

| Layer | Technologies |
|-------|--------------|
| **API** | FastAPI, Pydantic v2, Uvicorn/Gunicorn |
| **Data** | PostgreSQL, SQLAlchemy 2.0 (async), Alembic |
| **Async** | Celery, Redis |
| **ML** | pandas, NumPy, scikit-learn, XGBoost, LightGBM, CatBoost, Optuna, SHAP, MLflow |
| **Frontend** | React, TypeScript, TailwindCSS, TanStack Query, React Hook Form |
| **Infra** | Docker, Docker Compose, Nginx, GitHub Actions |
| **Quality** | pytest, coverage, Ruff, Black, mypy, Playwright |

## Architecture

Clean Architecture with the dependency rule pointing inwards:

```
              ┌──────────────────────────────────────────┐
  HTTP  ──▶   │  api/         routers, deps (DI), errors  │
              ├──────────────────────────────────────────┤
              │  services/    business logic (use-cases)  │
              ├──────────────────────────────────────────┤
              │  repositories/  data access (Repository)  │
              ├──────────────────────────────────────────┤
              │  models/      SQLAlchemy ORM              │
              └──────────────────────────────────────────┘
   supporting: schemas/ (DTOs) · storage/ (objects) · ml/ (framework-agnostic)
```

See [docs/architecture.md](docs/architecture.md) for diagrams and details.

## Quick start (backend)

```bash
# 1. Install dependencies into a virtualenv
make install

# 2. Copy and edit environment
cp backend/.env.example backend/.env

# 3. Run the API (http://localhost:8000/docs)
make run

# 4. Run the test suite
make test
```

> Full Docker Compose stack (Postgres, Redis, API, worker, MLflow, Nginx) lands
> in milestone **M9**; until then the API runs against the ORM and the suite runs
> on in-memory SQLite.

## Repository layout

```
.
├── backend/            FastAPI application, ML engine, tests
│   ├── app/
│   │   ├── api/        HTTP layer (routers, deps, middleware, errors)
│   │   ├── core/       config, logging, security, permissions
│   │   ├── db/         engine, session, base, mixins, seed
│   │   ├── models/     SQLAlchemy models
│   │   ├── repositories/ data access
│   │   ├── services/   business logic
│   │   ├── schemas/    Pydantic DTOs
│   │   ├── storage/    object storage abstraction
│   │   └── ml/         data loading, profiling, EDA, features, training
│   └── tests/          unit + integration tests
├── docs/               MkDocs documentation
├── ROADMAP.md          milestone plan
├── PROJECT_STATUS.md   current state
└── NEXT_TASK.md        the immediate next step
```

## License

[MIT](LICENSE) © 2026 Enterprise AutoML Platform
