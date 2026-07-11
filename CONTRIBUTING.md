# Contributing

Thanks for your interest in improving the Enterprise AutoML Platform.

## Getting set up

See [docs/installation.md](docs/installation.md). In short:

```bash
make install          # backend venv + deps
cd frontend && npm install
```

## Workflow

1. Branch from `main`.
2. Make a focused change following the [Developer Guide](docs/development.md)
   (vertical slice: model → repository → service → schema → endpoint → tests).
3. Run the quality gates locally (they must pass — CI enforces them):

   ```bash
   # backend
   cd backend && ruff check app tests && black --check app tests && mypy app && pytest
   # frontend
   cd frontend && npm run typecheck && npm run lint && npm run test && npm run build
   ```

4. Commit using [Conventional Commits](https://www.conventionalcommits.org):
   `feat(scope): …`, `fix(scope): …`, `test(...)`, `docs(...)`, etc. Keep commits
   small and atomic.
5. Open a pull request. CI runs backend, frontend and docs checks.

## Ground rules

- Type everything; keep `mypy` green.
- Raise domain errors from `app.core.exceptions`; never build HTTP responses in
  business logic.
- Guard endpoints with permissions and enforce ownership in services.
- Add tests for every behavioural change.
- Keep the project runnable at all times.
