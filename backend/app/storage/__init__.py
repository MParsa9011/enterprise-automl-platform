"""Object storage abstraction.

The application depends on the :class:`Storage` interface, never on a concrete
backend. A local-filesystem implementation ships by default; a cloud backend
(S3/GCS) can be dropped in without touching service code, satisfying the
dependency-inversion principle.
"""

from app.storage.base import Storage, StoredFile
from app.storage.local import LocalStorage

__all__ = ["Storage", "StoredFile", "LocalStorage"]
