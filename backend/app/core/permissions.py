"""Authorization catalog: the canonical set of permissions and roles.

This module is the single source of truth for *what capabilities exist* and
*which roles grant them*. The database is seeded from this catalog (see
:mod:`app.db.seed`), and application code references permission constants from
here rather than hard-coding strings, so a typo becomes an import error.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import Role


@dataclass(frozen=True, slots=True)
class PermissionSpec:
    """Declarative definition of a single permission."""

    resource: str
    action: str
    description: str

    @property
    def name(self) -> str:
        """The canonical ``resource:action`` permission name."""
        return f"{self.resource}:{self.action}"


# --- Permission catalog ------------------------------------------------------
PERMISSIONS: tuple[PermissionSpec, ...] = (
    PermissionSpec("project", "create", "Create projects"),
    PermissionSpec("project", "read", "View projects"),
    PermissionSpec("project", "update", "Modify projects"),
    PermissionSpec("project", "delete", "Delete projects"),
    PermissionSpec("dataset", "create", "Upload datasets"),
    PermissionSpec("dataset", "read", "View datasets and statistics"),
    PermissionSpec("dataset", "delete", "Delete datasets"),
    PermissionSpec("experiment", "create", "Launch AutoML experiments"),
    PermissionSpec("experiment", "read", "View experiments and runs"),
    PermissionSpec("experiment", "delete", "Delete experiments"),
    PermissionSpec("model", "read", "View registered models"),
    PermissionSpec("model", "deploy", "Deploy and promote models"),
    PermissionSpec("model", "delete", "Delete models"),
    PermissionSpec("prediction", "create", "Request predictions"),
    PermissionSpec("user", "read", "View users"),
    PermissionSpec("user", "manage", "Create, update and deactivate users"),
    PermissionSpec("audit", "read", "View audit logs"),
)

_ALL = {spec.name for spec in PERMISSIONS}
_READ_ONLY = {spec.name for spec in PERMISSIONS if spec.action == "read"}


@dataclass(frozen=True, slots=True)
class RoleSpec:
    """Declarative definition of a role and the permissions it grants."""

    name: str
    description: str
    permissions: frozenset[str]
    is_system: bool = True


# --- Role catalog ------------------------------------------------------------
ROLES: tuple[RoleSpec, ...] = (
    RoleSpec(
        name=Role.ADMIN,
        description="Full administrative access to every capability.",
        permissions=frozenset(_ALL),
    ),
    RoleSpec(
        name=Role.MANAGER,
        description="Manage projects and teams; read-only on models.",
        permissions=frozenset(
            _READ_ONLY
            | {
                "project:create",
                "project:update",
                "project:delete",
                "dataset:create",
                "experiment:create",
                "user:manage",
            }
        ),
    ),
    RoleSpec(
        name=Role.DATA_SCIENTIST,
        description="Build and manage own workspaces, run experiments, deploy models.",
        permissions=frozenset(
            _READ_ONLY
            | {
                # Full lifecycle over resources the user owns (ownership is
                # enforced per-instance in the service layer).
                "project:create",
                "project:update",
                "project:delete",
                "dataset:create",
                "dataset:delete",
                "experiment:create",
                "experiment:delete",
                "model:deploy",
                "prediction:create",
            }
        ),
    ),
    RoleSpec(
        name=Role.VIEWER,
        description="Read-only access to projects, datasets and results.",
        permissions=frozenset(_READ_ONLY),
    ),
)

# Convenient lookup used by the seeder and tests.
ROLE_BY_NAME: dict[str, RoleSpec] = {role.name: role for role in ROLES}
