"""Generic pagination, sorting and filtering DTOs.

``Page`` is a generic envelope returned by every list endpoint so that clients
get a uniform shape (items + metadata) regardless of the resource. ``PageParams``
is used as a FastAPI dependency to parse and validate common query parameters.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

from app.core.config import settings

T = TypeVar("T")


class SortOrder(StrEnum):
    """Sort direction for list queries."""

    ASC = "asc"
    DESC = "desc"


class PageParams(BaseModel):
    """Common pagination / sorting / search query parameters."""

    page: int = Field(default=1, ge=1, description="1-based page number.")
    size: int = Field(
        default=settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description="Number of items per page.",
    )
    sort_by: str | None = Field(default=None, description="Field name to sort by.")
    order: SortOrder = Field(default=SortOrder.DESC, description="Sort direction.")
    search: str | None = Field(default=None, max_length=255, description="Free-text search term.")

    @property
    def offset(self) -> int:
        """Zero-based offset derived from page and size."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Row limit for the query."""
        return self.size


class PageMeta(BaseModel):
    """Pagination metadata returned alongside a page of items."""

    page: int
    size: int
    total: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pages(self) -> int:
        """Total number of pages given the current page size."""
        if self.size == 0:
            return 0
        return (self.total + self.size - 1) // self.size

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_next(self) -> bool:
        """Whether a subsequent page exists."""
        return self.page < self.pages

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_prev(self) -> bool:
        """Whether a previous page exists."""
        return self.page > 1


class Page(BaseModel, Generic[T]):
    """A single page of results with pagination metadata."""

    items: list[T]
    meta: PageMeta

    @classmethod
    def create(cls, items: list[T], total: int, params: PageParams) -> "Page[T]":
        """Build a page envelope from raw items and the requesting params."""
        return cls(
            items=items,
            meta=PageMeta(page=params.page, size=params.size, total=total),
        )
