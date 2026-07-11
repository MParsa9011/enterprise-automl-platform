# AutoML Platform — Backend

FastAPI application and ML engine for the Enterprise AutoML Platform. See the
[repository README](../README.md) for the full project overview.

## Requirements

- Python 3.12+
- PostgreSQL 15+ and Redis 7+ (for the full stack; the test suite uses SQLite)

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ml]"

cp .env.example .env
uvicorn app.main:app --reload         # http://localhost:8000/docs
```

## Common tasks

| Command | Purpose |
|---------|---------|
| `pytest` | Run the test suite |
| `pytest --cov=app` | Tests with coverage |
| `ruff check app tests` | Lint |
| `black app tests` | Format |
| `mypy app` | Type-check |
| `alembic upgrade head` | Apply migrations |

## Layout

- `app/api` — routers, dependency injection, middleware, error handlers
- `app/core` — settings, logging, security, permissions, constants
- `app/db` — engine/session, declarative base, mixins, seeding
- `app/models` — SQLAlchemy ORM models
- `app/repositories` — data-access layer (Repository pattern)
- `app/services` — business logic (use-cases)
- `app/schemas` — Pydantic DTOs
- `app/storage` — object-storage abstraction
- `app/ml` — framework-agnostic ML (loading, profiling, EDA, features, training)
- `tests` — `unit/` and `integration/` suites
