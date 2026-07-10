"""Application exception hierarchy.

All expected error conditions are represented by subclasses of
:class:`AppError`. Each carries an HTTP status code, a stable machine-readable
``code`` (for clients to branch on) and an optional ``details`` payload. A single
exception handler (see :mod:`app.api.errors`) converts these into a consistent
JSON envelope, so business logic never needs to construct HTTP responses
directly — it simply raises the appropriate domain error.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all handled application errors."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Any | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    """The request was malformed or semantically invalid."""

    status_code = 400
    code = "bad_request"
    message = "The request could not be processed."


class ValidationError(BadRequestError):
    """A validation constraint was violated."""

    code = "validation_error"
    message = "The submitted data failed validation."


class AuthenticationError(AppError):
    """Authentication is required or the supplied credentials are invalid."""

    status_code = 401
    code = "authentication_error"
    message = "Authentication credentials were not valid."


class PermissionDeniedError(AppError):
    """The authenticated principal lacks permission for this action."""

    status_code = 403
    code = "permission_denied"
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    """The requested resource does not exist."""

    status_code = 404
    code = "not_found"
    message = "The requested resource was not found."


class ConflictError(AppError):
    """The request conflicts with the current state of the resource."""

    status_code = 409
    code = "conflict"
    message = "The request conflicts with the current resource state."


class UnprocessableEntityError(AppError):
    """The request was well-formed but cannot be processed."""

    status_code = 422
    code = "unprocessable_entity"
    message = "The request could not be processed."


class RateLimitExceededError(AppError):
    """The client has exceeded the permitted request rate."""

    status_code = 429
    code = "rate_limit_exceeded"
    message = "Rate limit exceeded. Please retry later."


class ServiceUnavailableError(AppError):
    """A downstream dependency is unavailable."""

    status_code = 503
    code = "service_unavailable"
    message = "The service is temporarily unavailable."
