"""Repository base classes (async).

`TenantScopedRepository` is the mechanism that makes cross-tenant access hard by
construction: it cannot be built without a `TenantContext`, every read starts
from a tenant-filtered SELECT, and every write stamps the context's tenant id
over whatever the caller supplied.

The generic helpers here (`find_one`, `exists`, `paginate`) exist so concrete
repositories only describe WHAT they select - the filtering, counting and paging
mechanics are written once.

Repositories perform data access only - no business rules, no commits.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Row, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import NotFoundError
from app.core.pagination import Pagination
from app.core.tenant_context import TenantContext
from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)

#: Applied to the page query only (e.g. to add eager loading), never to COUNT.
Decorator = Callable[[Select[Any]], Select[Any]]


class BaseRepository(Generic[ModelT]):
    """Data access for a model that is NOT tenant-owned (e.g. tenants themselves)."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------ selecting

    def base_select(self) -> Select[tuple[ModelT]]:
        """The starting point of every read in this repository."""
        return select(self.model)

    async def find_one(self, *conditions: ColumnElement[bool]) -> ModelT | None:
        """First row matching the conditions, within this repository's scope."""
        return await self.session.scalar(self.base_select().where(*conditions))

    async def exists(self, *conditions: ColumnElement[bool]) -> bool:
        return await self.find_one(*conditions) is not None

    async def get(self, entity_id: UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    # ------------------------------------------------------------- counting

    async def count(self, statement: Select[Any] | None = None) -> int:
        stmt = statement if statement is not None else self.base_select()
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery()))
        return int(total or 0)

    async def paginate(
        self,
        statement: Select[Any],
        pagination: Pagination,
        *,
        decorate: Decorator | None = None,
    ) -> tuple[list[ModelT], int]:
        """Return one page of rows plus the total count of the full query."""
        total = await self.count(statement)
        page = statement.offset(pagination.offset).limit(pagination.limit)
        if decorate is not None:
            page = decorate(page)
        rows = await self.session.scalars(page)
        return list(rows), total

    async def paginate_rows(
        self, statement: Select[Any], pagination: Pagination
    ) -> tuple[Sequence[Row[Any]], int]:
        """As `paginate`, for queries that select several entities per row."""
        total = await self.count(statement)
        page = statement.offset(pagination.offset).limit(pagination.limit)
        result = await self.session.execute(page)
        return result.all(), total

    # -------------------------------------------------------------- writing

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()


class TenantScopedRepository(BaseRepository[ModelT]):
    """Data access for tenant-owned models. Always filtered by tenant."""

    def __init__(self, session: AsyncSession, tenant: TenantContext) -> None:
        super().__init__(session)
        self.tenant = tenant

    @property
    def tenant_id(self) -> UUID:
        return self.tenant.tenant_id

    def base_select(self) -> Select[tuple[ModelT]]:
        """Start every query from a tenant-filtered SELECT."""
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    async def get(self, entity_id: UUID) -> ModelT | None:
        """Fetch by primary key, scoped to the tenant.

        A row belonging to another tenant is indistinguishable from a missing
        row, which is what prevents cross-tenant existence probing.
        """
        return await self.find_one(self.model.id == entity_id)

    async def get_or_raise(self, entity_id: UUID, *, resource: str | None = None) -> ModelT:
        entity = await self.get(entity_id)
        if entity is None:
            raise NotFoundError(f"{resource or self.model.__name__} not found")
        return entity

    async def add(self, entity: ModelT) -> ModelT:
        """Persist a new row, forcing it into the current tenant."""
        entity.tenant_id = self.tenant_id
        self.session.add(entity)
        await self.session.flush()
        return entity
