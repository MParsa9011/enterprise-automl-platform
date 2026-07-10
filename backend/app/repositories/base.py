"""Generic asynchronous repository.

:class:`BaseRepository` provides the CRUD, counting, pagination, sorting and
search primitives shared by every concrete repository, parameterised over the
ORM model type. Concrete repositories subclass it, bind a ``model`` and add only
the queries specific to their aggregate — eliminating the boilerplate that would
otherwise be duplicated across a dozen data-access classes.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, asc, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.db.base_class import Base
from app.schemas.pagination import PageParams, SortOrder

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Async CRUD repository bound to a single ORM model."""

    #: The ORM model managed by this repository. Set by subclasses.
    model: type[ModelT]

    #: Columns eligible for free-text ``ILIKE`` search, set by subclasses.
    searchable_fields: tuple[str, ...] = ()

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        """Return the entity with ``entity_id`` or ``None`` if absent."""
        return await self.session.get(self.model, entity_id)

    async def get_by(self, **filters: Any) -> ModelT | None:
        """Return the first entity matching the equality ``filters``."""
        stmt = self._apply_filters(select(self.model), filters).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, **filters: Any) -> bool:
        """Return whether any entity matches the equality ``filters``."""
        stmt = self._apply_filters(select(self.model.id), filters).limit(1)
        result = await self.session.execute(stmt)
        return result.first() is not None

    async def count(self, **filters: Any) -> int:
        """Count entities matching the equality ``filters``."""
        stmt = self._apply_filters(select(func.count()).select_from(self.model), filters)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list(
        self,
        params: PageParams,
        *,
        filters: dict[str, Any] | None = None,
    ) -> tuple[Sequence[ModelT], int]:
        """Return a page of entities and the total count matching the query.

        Applies equality filters, free-text search across ``searchable_fields``,
        ordering and limit/offset pagination in a single round-trip pair (one
        query for the page, one for the total).
        """
        base = self._apply_filters(select(self.model), filters or {})
        base = self._apply_search(base, params.search)

        total_stmt = select(func.count()).select_from(base.order_by(None).subquery())
        total = int((await self.session.execute(total_stmt)).scalar_one())

        stmt = self._apply_ordering(base, params).offset(params.offset).limit(params.limit)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    async def create(self, **data: Any) -> ModelT:
        """Instantiate, persist and flush a new entity."""
        entity = self.model(**data)
        return await self.add(entity)

    async def add(self, entity: ModelT) -> ModelT:
        """Add an existing entity instance to the session and flush."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT, **data: Any) -> ModelT:
        """Apply ``data`` to ``entity`` in place and flush the changes."""
        for key, value in data.items():
            setattr(entity, key, value)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Delete a single entity instance."""
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, entity_id: uuid.UUID) -> int:
        """Bulk-delete by primary key, returning the number of rows removed."""
        stmt = delete(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    # ------------------------------------------------------------------
    # Query construction helpers
    # ------------------------------------------------------------------
    def _column(self, name: str) -> InstrumentedAttribute[Any] | None:
        """Resolve a mapped column by name, or ``None`` if it does not exist."""
        attr = getattr(self.model, name, None)
        return attr if isinstance(attr, InstrumentedAttribute) else None

    def _apply_filters(self, stmt: Select[Any], filters: dict[str, Any]) -> Select[Any]:
        """Add equality ``WHERE`` clauses for each recognised filter key."""
        for key, value in filters.items():
            column = self._column(key)
            if column is not None and value is not None:
                stmt = stmt.where(column == value)
        return stmt

    def _apply_search(self, stmt: Select[Any], term: str | None) -> Select[Any]:
        """Add a case-insensitive ``OR`` search across searchable fields."""
        if not term or not self.searchable_fields:
            return stmt
        pattern = f"%{term}%"
        clauses = [
            col.ilike(pattern)
            for name in self.searchable_fields
            if (col := self._column(name)) is not None
        ]
        if not clauses:
            return stmt
        return stmt.where(or_(*clauses))

    def _apply_ordering(self, stmt: Select[Any], params: PageParams) -> Select[Any]:
        """Order by the requested column, defaulting to ``created_at``."""
        column = self._column(params.sort_by or "") or self._column("created_at")
        if column is None:
            return stmt
        direction = desc if params.order == SortOrder.DESC else asc
        return stmt.order_by(direction(column))
