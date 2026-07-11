"""Centralised exception handlers.

Every error — whether a domain :class:`AppError`, a FastAPI/Starlette
``HTTPException`` or an unexpected exception — is funnelled through one of these
handlers and rendered as the same :class:`ErrorResponse` envelope. This keeps the
API contract consistent and ensures unexpected errors never leak stack traces to
clients while still being logged with full context server-side.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.response import ErrorDetail, ErrorResponse

logger = get_logger(__name__)


def _render(request: Request, status_code: int, detail: ErrorDetail) -> JSONResponse:
    """Serialise an error into the standard envelope with the request id."""
    request_id = getattr(request.state, "request_id", None)
    payload = ErrorResponse(error=detail, request_id=request_id)
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


def _safe_validation_errors(errors: Sequence[Any]) -> list[dict[str, Any]]:
    """Return JSON-safe validation errors.

    Pydantic embeds the originating exception in each error's ``ctx`` (e.g.
    ``ctx={"error": ValueError(...)}``), which is not JSON-serialisable. We
    stringify ``ctx`` values and normalise ``loc`` to a plain list so the payload
    can be rendered without leaking non-serialisable objects.
    """
    cleaned: list[dict[str, Any]] = []
    for error in errors:
        item: dict[str, Any] = dict(error)
        loc = item.get("loc")
        if isinstance(loc, tuple):
            item["loc"] = list(loc)
        ctx = item.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {str(key): str(value) for key, value in ctx.items()}
        cleaned.append(item)
    return cleaned


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all application exception handlers to ``app``."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        # Client errors are expected; log at info. Server errors are not.
        log = logger.warning if exc.status_code < 500 else logger.error
        log(
            "app_error",
            code=exc.code,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return _render(
            request,
            exc.status_code,
            ErrorDetail(code=exc.code, message=exc.message, details=exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _render(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorDetail(
                code="validation_error",
                message="Request validation failed.",
                details=_safe_validation_errors(exc.errors()),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _render(
            request,
            exc.status_code,
            ErrorDetail(code="http_error", message=str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", path=request.url.path)
        return _render(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorDetail(code="internal_error", message="An unexpected error occurred."),
        )
