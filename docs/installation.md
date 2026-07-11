# Installation

## Prerequisites

- Python 3.12+
- Node 20+
- (For the full stack) Docker & Docker Compose
- (Optional, for local ML libs) OpenMP runtime — `brew install libomp` on macOS

## Option A — Docker Compose (recommended)

The fastest way to run the whole platform:

```bash
cp .env.example .env
# edit .env: set SECRET_KEY and the superuser credentials
docker compose up -d --build
```

Then open:

| Service | URL |
|---------|-----|
| Frontend | <http://localhost:8080> |
| API docs (Swagger) | <http://localhost:8000/docs> |
| MLflow | <http://localhost:5000> |

The API container waits for Postgres, applies migrations and seeds the RBAC
catalog plus the bootstrap superuser on start-up.

## Option B — Run the backend locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ml]"

cp .env.example .env          # point POSTGRES_* at a local Postgres
alembic upgrade head          # create the schema
python -m app.db.init_db      # seed RBAC + superuser

uvicorn app.main:app --reload # http://localhost:8000/docs
```

To run the Celery worker (needs Redis):

```bash
celery -A app.worker.celery_app worker --loglevel=info
```

!!! tip "SQLite for tests"
    The test suite runs on a throwaway SQLite database and needs no external
    services: `pytest`.

## Option C — Run the frontend locally

```bash
cd frontend
npm install
cp .env.example .env          # the dev server proxies /api to the backend
npm run dev                   # http://localhost:5173
```

## Verifying

```bash
# Backend quality gates
cd backend && ruff check app tests && black --check app tests && mypy app && pytest

# Frontend quality gates
cd frontend && npm run typecheck && npm run lint && npm run test && npm run build
```
