# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ |
| < 1.0   | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Instead, report them privately via GitHub's
[private vulnerability reporting](https://github.com/MParsa9011/enterprise-automl-platform/security/advisories/new)
(Security → Advisories → *Report a vulnerability*), or email the maintainers.

Please include:

- a description of the vulnerability and its impact,
- steps to reproduce (a minimal proof-of-concept if possible),
- affected version(s) and configuration.

We aim to acknowledge reports within **72 hours** and to provide a remediation
timeline after triage. We will credit reporters in the release notes unless you
prefer to remain anonymous.

## Security practices in this project

- Secrets are supplied via environment variables; **no `.env` file, credential or
  token is ever committed** (only `.env.example` templates).
- Passwords are hashed with **bcrypt**; JWT refresh tokens are rotated and revocable.
- The API enforces **RBAC** and applies conservative security headers, CORS and
  trusted-host restrictions.
- Dependencies are monitored via **Dependabot**.

When deploying, always set a strong `SECRET_KEY`, change the default superuser
credentials, run behind TLS, and restrict `BACKEND_CORS_ORIGINS` and `ALLOWED_HOSTS`.
