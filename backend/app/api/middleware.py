"""Custom ASGI middleware.

* :class:`RequestContextMiddleware` assigns every request a correlation id
  (respecting an inbound ``X-Request-ID`` when present), binds it to the
  structlog context so *all* log lines emitted while handling the request carry
  it, records wall-clock latency and emits a structured access log.

Security headers are applied separately in the app factory via a lightweight
middleware so that concerns stay small and independently testable.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import REQUEST_ID_HEADER
from app.core.logging import get_logger

logger = get_logger(__name__)

CallNext = Callable[[Request], Awaitable[Response]]

# HTTP methods whose requests mutate state and are therefore audited.
_AUDITED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_API_PREFIX = "/api/v1/"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a correlation id and emit structured access logs."""

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception("request_failed", duration_ms=round(elapsed_ms, 2))
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.2f}"

        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(elapsed_ms, 2),
        )
        structlog.contextvars.clear_contextvars()
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Persist an audit record for every mutating request.

    Writes use a short-lived session obtained from ``app.state.session_factory``
    (overridable in tests), independent of the request's own session which is
    already closed by the time this post-processing runs. Failures are swallowed
    so auditing can never break the actual request.
    """

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        response = await call_next(request)
        if request.method in _AUDITED_METHODS and self._is_api(request):
            try:
                await self._record(request, response)
            except Exception:  # noqa: BLE001 - auditing must never break a request
                logger.warning("audit_write_failed", path=request.url.path)
        return response

    @staticmethod
    def _is_api(request: Request) -> bool:
        return request.url.path.startswith(_API_PREFIX)

    async def _record(self, request: Request, response: Response) -> None:
        session_factory = getattr(request.app.state, "session_factory", None)
        if session_factory is None:
            return

        from app.repositories.audit import AuditLogRepository

        resource_type, resource_id = self._resource(request.url.path)
        user_id = self._user_id(request)
        forwarded = request.headers.get("x-forwarded-for")
        ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else None
        )

        async with session_factory() as session:
            repo = AuditLogRepository(session)
            await repo.record(
                user_id=user_id,
                action=f"{request.method} {request.url.path}",
                resource_type=resource_type,
                resource_id=resource_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                ip_address=ip,
                user_agent=request.headers.get("user-agent", "")[:400] or None,
                request_id=getattr(request.state, "request_id", None),
            )
            await session.commit()

    @staticmethod
    def _resource(path: str) -> tuple[str | None, str | None]:
        """Extract a resource type and optional id from the request path."""
        parts = [segment for segment in path[len(_API_PREFIX):].split("/") if segment]
        if not parts:
            return None, None
        resource_type = parts[0]
        resource_id = None
        if len(parts) > 1 and _looks_like_id(parts[1]):
            resource_id = parts[1]
        return resource_type, resource_id

    @staticmethod
    def _user_id(request: Request) -> uuid.UUID | None:
        """Best-effort extraction of the acting user from the bearer token."""
        from app.core.security import TokenType, decode_token

        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return None
        try:
            payload = decode_token(header.split(" ", 1)[1], expected_type=TokenType.ACCESS)
            return payload.user_id
        except Exception:  # noqa: BLE001 - unauthenticated/invalid tokens are fine
            return None


def _looks_like_id(value: str) -> bool:
    """Heuristic: treat UUID-like path segments as resource ids."""
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply a conservative set of security response headers."""

    def __init__(self, app: Callable, *, hsts: bool = False) -> None:  # type: ignore[type-arg]
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if self._hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response
