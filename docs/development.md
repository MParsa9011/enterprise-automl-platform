# Developer Guide

## Repository layout

```
backend/
  app/
    api/          HTTP layer — routers, deps (DI), middleware, error handlers
    core/         settings, logging, security, permissions, constants, utils
    db/           engine/session, declarative base, mixins, seeding, migrations
    models/       SQLAlchemy ORM models
    repositories/ data-access layer (Repository pattern)
    services/     business logic (use-cases)
    schemas/      Pydantic DTOs
    storage/      object-storage abstraction (local + swappable backends)
    ml/           framework-agnostic ML (io, profiling, eda, features, algorithms,
                  evaluation, training, explain, tracking)
    worker/       Celery app and tasks
  alembic/        migrations
  tests/          unit/ and integration/ suites
frontend/
  src/
    lib/          API client, token store, query client, utils
    context/      auth provider + context
    hooks/        TanStack Query data hooks
    components/   UI primitives + layout (shell, sidebar, topbar)
    pages/        route screens
```

## Adding a feature (the vertical slice)

Follow the same pattern the codebase already uses:

1. **Model** (`app/models`) — add the ORM entity; register it in `app/db/base.py`.
2. **Migration** — `alembic revision --autogenerate -m "add X"`.
3. **Repository** (`app/repositories`) — extend `BaseRepository[X]`.
4. **Schemas** (`app/schemas`) — request/response DTOs.
5. **Service** (`app/services`) — the use-case + authorization rules.
6. **Endpoint** (`app/api/v1/endpoints`) — thin router; wire providers in
   `app/api/deps.py` and include the router in `app/api/v1/router.py`.
7. **Tests** (`tests/`) — unit tests for pure logic, integration tests for the
   endpoint.

## Conventions

- **Typing** — full type hints; `mypy app` must pass.
- **Docstrings** — module and public-symbol docstrings explain the *why*.
- **Errors** — raise a domain error from `app.core.exceptions`; never build HTTP
  responses in business logic.
- **Authorization** — guard endpoints with `require_permissions(...)`; enforce
  per-instance ownership in the service.
- **Async** — offload CPU-bound work (parsing, training) with
  `anyio.to_thread.run_sync`.

## Quality gates

```bash
# Backend
cd backend
ruff check app tests        # lint
black app tests             # format
mypy app                    # types
pytest --cov=app            # tests + coverage

# Frontend
cd frontend
npm run typecheck && npm run lint && npm run test && npm run build
```

Or use the root `Makefile`: `make lint`, `make test`, `make format`.

## Commit conventions

Commits follow [Conventional Commits](https://www.conventionalcommits.org):
`feat(scope): …`, `fix(scope): …`, `refactor(...)`, `test(...)`, `docs(...)`,
`ci(...)`, `build(...)`, `style(...)`, `perf(...)`, `chore(...)`.
