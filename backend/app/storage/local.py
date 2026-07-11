"""Local-filesystem storage backend.

Writes objects beneath a configurable root directory. Blocking file IO is
off-loaded to a worker thread via :mod:`anyio` so it never stalls the event
loop. Keys are treated as relative paths; traversal outside the root is rejected.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import anyio

from app.storage.base import Storage, StoredFile


class LocalStorage(Storage):
    """Store objects on the local filesystem under ``root``."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Resolve ``key`` to an absolute path, guarding against traversal."""
        candidate = (self._root / key).resolve()
        if not candidate.is_relative_to(self._root):
            raise ValueError(f"Refusing to access path outside storage root: {key!r}")
        return candidate

    async def save(
        self, key: str, data: bytes, *, content_type: str | None = None
    ) -> StoredFile:
        path = self._resolve(key)
        await anyio.to_thread.run_sync(lambda: path.parent.mkdir(parents=True, exist_ok=True))
        await anyio.to_thread.run_sync(path.write_bytes, data)
        checksum = hashlib.sha256(data).hexdigest()
        return StoredFile(
            key=key,
            size_bytes=len(data),
            checksum=checksum,
            content_type=content_type,
        )

    async def read(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(key)
        return await anyio.to_thread.run_sync(path.read_bytes)

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        await anyio.to_thread.run_sync(path.unlink, True)  # missing_ok=True

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def local_path(self, key: str) -> str:
        return str(self._resolve(key))
