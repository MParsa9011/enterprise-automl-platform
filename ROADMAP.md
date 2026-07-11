# Roadmap — Enterprise AutoML Platform

Milestones are delivered as vertical slices (model → repository → service → DTO →
API → tests) with atomic Conventional Commits. Each milestone is production-ready
before the next begins; the project stays runnable throughout.

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Backend foundation & core infrastructure | ✅ Done |
| M2 | Authentication & authorization (JWT, RBAC, refresh rotation) | ✅ Done |
| M3 | Workspace & project management | ✅ Done |
| M4 | Dataset management (upload, versioning, statistics) | ✅ Done |
| M5 | EDA & feature engineering pipeline | ✅ Done |
| M6 | AutoML training engine (Celery, Optuna, MLflow) | ✅ Done |
| M7 | Model registry, prediction API, notifications, audit logs | ✅ Done |
| M8 | Frontend admin dashboard (React + TS + Tailwind) | ✅ Done |
| M9 | DevOps, CI/CD, docs, migrations & deployment | ✅ Done |

> **All milestones complete.** The platform is fully implemented, tested,
> containerised, documented and CI-gated.

## Milestone detail

### M5 — EDA & feature engineering
Automated EDA artifacts (missing-value maps, distributions, box/scatter plots,
correlation heatmaps) generated as Plotly-compatible JSON, plus a configurable
feature-engineering pipeline (imputation, encoding, scaling, feature selection,
PCA) built on scikit-learn `Pipeline`/`ColumnTransformer`.

### M6 — AutoML training engine
`Experiment` / `Run` / `Model` domain, Celery async training tasks, an algorithm
registry (Random Forest, XGBoost, CatBoost, LightGBM, Logistic Regression, SVM,
KNN, Naive Bayes, Decision Tree, Extra Trees, Gradient Boosting), Optuna HPO,
evaluation metrics (ROC/AUC, confusion matrix, precision/recall/F1, learning
curves) and SHAP explainability, tracked in MLflow.

### M7 — Registry, prediction, notifications, audit
Model versioning/compare/deploy, JSON prediction API, in-app notifications and a
structured audit-log trail.

### M8 — Frontend
Vite + React + TypeScript + Tailwind + TanStack Query admin dashboard with dark
mode, charts, tables, loading/error states.

### M9 — DevOps & docs
Dockerfiles, docker-compose, Nginx, GitHub Actions CI/CD, Alembic migrations,
MkDocs, architecture & ER diagrams, deployment guide.
