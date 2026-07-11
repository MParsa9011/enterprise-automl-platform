"""Metadata aggregator for Alembic autogeneration.

Alembic compares the live database against ``Base.metadata`` to emit migrations.
For that comparison to be complete, *every* ORM model must be imported so its
table is registered on the shared metadata. This module is the single place that
imports them all; new models must be added here as they are created.
"""

from __future__ import annotations

from app.db.base_class import Base

# Model imports are for their side effect (table registration) only; new models
# must be added here so Alembic autogeneration sees them.
from app.models.dataset import Dataset, DatasetVersion  # noqa: F401, E402
from app.models.experiment import Experiment, Run  # noqa: F401, E402
from app.models.permission import Permission  # noqa: F401, E402
from app.models.project import Project  # noqa: F401, E402
from app.models.refresh_token import RefreshToken  # noqa: F401, E402
from app.models.role import Role  # noqa: F401, E402
from app.models.user import User  # noqa: F401, E402

__all__ = ["Base"]
