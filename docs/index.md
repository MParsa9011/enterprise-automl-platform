# Enterprise AutoML Platform

A production-grade platform for automated machine learning: upload data, run
automated EDA and feature engineering, train and tune dozens of models, explain
them, and serve predictions through a versioned model registry.

## What it does

| Capability | Summary |
|------------|---------|
| **Auth & RBAC** | JWT access/refresh tokens with rotation, roles and fine-grained permissions |
| **Workspaces** | Projects that own datasets, experiments and models |
| **Datasets** | CSV/Excel/Parquet upload, immutable versioning, automated statistical profiling |
| **EDA** | Missing-value maps, distributions, box/scatter plots, correlation heatmaps |
| **Feature engineering** | Imputation, encoding, scaling, feature selection, PCA |
| **AutoML** | 11 algorithms, Optuna hyper-parameter optimisation, MLflow tracking |
| **Explainability** | SHAP, permutation importance |
| **Registry** | Model versioning, comparison, staged deployment |
| **Prediction** | JSON-in / predictions-out from deployed models |
| **Ops** | Notifications, structured audit logs |

## Tech stack

- **API:** FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), PostgreSQL, Alembic
- **Async:** Celery, Redis
- **ML:** pandas, NumPy, scikit-learn, XGBoost, LightGBM, CatBoost, Optuna, SHAP, MLflow
- **Frontend:** React, TypeScript, TailwindCSS, TanStack Query
- **Infra:** Docker, Docker Compose, Nginx, GitHub Actions

## Where to go next

- [Architecture](architecture.md) — the layered design and request flow
- [Database (ER)](database.md) — the relational schema
- [Installation](installation.md) — run it locally
- [Deployment](deployment.md) — the Docker Compose stack
- [Developer Guide](developer-guide.md) — conventions and workflows
- [API Reference](api.md) — endpoint overview
