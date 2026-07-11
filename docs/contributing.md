# Contributing

The full contributor guide lives at the repository root:
**[CONTRIBUTING.md](https://github.com/your-org/enterprise-automl-platform/blob/main/CONTRIBUTING.md)**.

In brief:

1. Read the [Development](development.md) workflow and [Coding Standards](coding-standards.md).
2. Branch from `main`, make a focused vertical-slice change, and add tests.
3. Ensure every quality gate is green:
   ```bash
   cd backend  && ruff check app tests && black --check app tests && mypy app && pytest
   cd frontend && npm run typecheck && npm run lint && npm run test && npm run build
   ```
4. Use small, atomic [Conventional Commits](https://www.conventionalcommits.org).
5. Open a pull request using the provided template; CI runs backend, frontend and
   docs checks.

Please also review the [Code of Conduct](https://github.com/your-org/enterprise-automl-platform/blob/main/CODE_OF_CONDUCT.md)
and report security issues per the [Security Policy](https://github.com/your-org/enterprise-automl-platform/blob/main/SECURITY.md).
