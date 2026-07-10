"""Standard response envelopes for errors and simple messages."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine-readable description of a single error."""

    code: str = Field(description="Stable, machine-readable error code.")
    message: str = Field(description="Human-readable error message.")
    details: Any | None = Field(default=None, description="Optional structured context.")


class ErrorResponse(BaseModel):
    """Uniform error envelope returned for every non-2xx response."""

    error: ErrorDetail
    request_id: str | None = Field(default=None, description="Correlation id for this request.")


class MessageResponse(BaseModel):
    """Simple acknowledgement payload for actions without a resource body."""

    message: str
    detail: str | None = None
