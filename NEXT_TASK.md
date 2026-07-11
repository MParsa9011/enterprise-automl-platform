# Next Task

## ▶ M9 — DevOps, CI/CD, Docs & Deployment (final milestone)

**Goal:** Make the platform reproducibly buildable, deployable and documented.

### Scope
1. **Containerisation**
   - Multi-stage backend `Dockerfile` (API + worker share the image).
   - Frontend `Dockerfile` (Vite build → Nginx static serve).
   - `.dockerignore` for both.
2. **Orchestration**
   - `docker-compose.yml`: Postgres, Redis, API, Celery worker, MLflow, frontend
     (Nginx reverse proxy for `/api`), with healthchecks and named volumes.
   - `.env.example` at the compose level.
3. **Database migrations**
   - Generate the initial Alembic migration for the full schema.
   - Entrypoint that runs `alembic upgrade head` + RBAC/superuser seeding.
4. **CI/CD** (`.github/workflows/`)
   - Backend: Ruff, Black, mypy, pytest (Postgres + Redis services).
   - Frontend: typecheck, ESLint, build, Vitest.
   - Docker build validation.
5. **Documentation** (MkDocs)
   - `mkdocs.yml` + pages: index, architecture (diagram), ER diagram, installation,
     deployment, developer guide, API overview.
6. **Ops polish**
   - Root `.env.example`, `CONTRIBUTING.md`, license already present.

### Definition of done
- `docker compose config` validates; images build.
- CI workflows are valid and cover both apps.
- Migration applies cleanly; seeding runs on startup.
- MkDocs site builds; diagrams render.
- Roadmap fully green; this file notes project completion.
