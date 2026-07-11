# 🚀 Enterprise AutoML Platform v1.0.0

The first public release — a complete, production-grade platform for automated
machine learning. Upload data, run automated EDA and feature engineering, train
and tune dozens of models, explain them, and serve predictions through a versioned
model registry.

## Highlights

- 🔐 **Auth & RBAC** — JWT access + refresh tokens with rotation/revocation and
  fine-grained permissions.
- 📊 **Datasets** — CSV/Excel/Parquet upload, immutable versioning, automated
  statistical profiling and EDA.
- 🧪 **Feature engineering** — imputation, encoding, scaling, selection, PCA.
- ⚙️ **AutoML** — 11 algorithms, Optuna hyper-parameter tuning, MLflow tracking.
- 🧠 **Explainability** — SHAP + permutation importance.
- 📦 **Registry & serving** — model versioning, staged deployment, JSON prediction API.
- 🖥️ **Dashboard** — React + TypeScript admin UI with dark mode.
- 🐳 **Ops** — Docker Compose stack, CI/CD, and full documentation.

## Getting started

```bash
cp .env.example .env          # set SECRET_KEY + superuser credentials
docker compose up -d --build
```

- Frontend → http://localhost:8080
- API docs → http://localhost:8000/docs
- MLflow → http://localhost:5000

See the [README](README.md) and [docs/](docs/) for full instructions.

## Quality

- Backend: Ruff, Black, mypy and **84 passing tests** (SQLite-backed, no external
  services needed).
- Frontend: strict TypeScript, ESLint, Vitest and a production build — all green.
- The complete user journey (register → dataset → train → deploy → predict) was
  verified end-to-end against a live PostgreSQL database.

## Compatibility

- Python 3.12+, Node 20+, PostgreSQL 15+, Redis 7+.

## Tech stack

FastAPI · SQLAlchemy 2.0 · PostgreSQL · Celery · Redis · scikit-learn · XGBoost ·
LightGBM · CatBoost · Optuna · SHAP · MLflow · React · TypeScript · TailwindCSS ·
Docker · GitHub Actions.

**Full changelog:** [CHANGELOG.md](CHANGELOG.md)
