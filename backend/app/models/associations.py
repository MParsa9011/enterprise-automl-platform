"""Association tables for many-to-many relationships.

These are plain Core ``Table`` objects (no ORM class) because they carry no
attributes of their own — they exist purely to join two aggregates. Defining
them centrally avoids import cycles between the models they connect.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Table

from app.db.base_class import Base

# users <-> roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# roles <-> permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
