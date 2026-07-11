"""Storage interface and value objects."""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredFile:
    """Metadata describing a persisted object."""

    key: str
    size_bytes: int
    checksum: str
    content_type: str | None = None


class Storage(abc.ABC):
    """Abstract binary object store keyed by opaque string keys."""

    @abc.abstractmethod
    async def save(self, key: str, data: bytes, *, content_type: str | None = None) -> StoredFile:
        """Persist ``data`` under ``key`` and return its metadata."""

    @abc.abstractmethod
    async def read(self, key: str) -> bytes:
        """Return the bytes stored under ``key``."""

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        """Remove the object at ``key`` (idempotent)."""

    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether an object exists at ``key``."""

    @abc.abstractmethod
    def local_path(self, key: str) -> str:
        """Return a filesystem path for ``key`` for libraries needing a path.

        Backends without local materialisation should raise
        :class:`NotImplementedError`; callers then fall back to :meth:`read`.
        """
