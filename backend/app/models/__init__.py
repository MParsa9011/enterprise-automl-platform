"""SQLAlchemy ORM models.

Each aggregate lives in its own module. ``app.db.base`` imports them all so that
Alembic and the metadata registry see every table.
"""
