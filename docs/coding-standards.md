# Coding Standards

These standards are enforced by tooling and CI — a change is not mergeable until
they pass.

## Backend (Python)

| Tool | Rule |
|------|------|
| **Ruff** | Lint + import sorting (`E, W, F, I, N, UP, B, C4, SIM, TID, RUF`), line length 100 |
| **Black** | Formatting, line length 100 |
| **mypy** | `disallow_untyped_defs`, `check_untyped_defs`; ML libraries are `ignore_missing_imports` |
| **pytest** | `--strict-markers --strict-config`; markers: `unit`, `integration`, `ml` |

Run all gates: `ruff check app tests && black --check app tests && mypy app && pytest`.

### Conventions

- **Type hints everywhere.** Public functions and methods must be fully typed.
- **Docstrings** on modules and public symbols explain the *why*, not the *what*.
- **Comments** only where the intent isn't obvious from the code.
- **Errors:** raise a domain error from `app.core.exceptions`; never construct HTTP
  responses in business logic. A single handler renders the uniform envelope.
- **Authorization:** guard endpoints with `require_permissions(...)`; enforce
  per-instance ownership in the service layer (return *not found*, not *forbidden*,
  for cross-owner access to avoid leaking existence).
- **Async:** offload CPU-bound work (parsing, training) with
  `anyio.to_thread.run_sync`; never block the event loop.
- **Repositories** are the only layer that touches the ORM; services depend on
  repository abstractions.
- **Prefer readability over cleverness.**

## Frontend (TypeScript)

| Tool | Rule |
|------|------|
| **TypeScript** | `strict: true`, `noUnusedLocals`, `noUnusedParameters` |
| **ESLint** | flat config with `typescript-eslint` + react-hooks; `--max-warnings 0` |
| **Prettier** | 2-space indent, double quotes, trailing commas, width 100 |

### Conventions

- Components are typed function components; hooks encapsulate data access.
- Keep the fast-refresh rule happy — one component per file where practical, and
  keep non-component exports (context, hooks) in separate files.
- Use the shared `cn()` helper for conditional Tailwind classes.
- Every list/query surface has explicit loading / error / empty states.

## Commits

Small, atomic [Conventional Commits](https://www.conventionalcommits.org):

```
feat(scope): …     a new capability
fix(scope): …      a bug fix
refactor(scope): … behaviour-preserving change
test(scope): …     tests only
docs(scope): …     documentation
ci(scope): …       CI/automation
build(scope): …    build system / deps
style(scope): …    formatting only
chore(scope): …    housekeeping
```

One logical change per commit; keep the repository runnable at every commit.
