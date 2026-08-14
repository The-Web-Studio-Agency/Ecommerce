"""Tenant-scoped repository base.

This exists for exactly one reason: tenant isolation must not depend on every
developer remembering to write `WHERE tenant_id = ...` in every query. A
repository that extends `TenantScopedRepository` cannot be constructed without a
tenant id, starts every read from a tenant-filtered SELECT, and stamps that
tenant id onto every write.

It is deliberately small. There is no pagination, no query-decorator hook, no
generic CRUD - add those to a concrete repository when a real endpoint needs
them.

Auth-layer lookups (`users`, `tenants`) do NOT use this: authentication has to
find a user before a tenant is known, so those repositories are plain classes
that take an explicit tenant id.
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantScopedRepository(Generic[ModelT]):
    """Data access for a tenant-owned model. Every query is tenant-filtered."""

    #: The model this repository reads and writes. Must have a `tenant_id`.
    model: type[ModelT]

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def base_select(self) -> Select[tuple[ModelT]]:
        """The starting point of every read. Subclasses build on this."""
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    async def find_one(self, *conditions: ColumnElement[bool]) -> ModelT | None:
        return await self.session.scalar(self.base_select().where(*conditions))

    async def get(self, entity_id: UUID) -> ModelT | None:
        """Fetch by primary key, scoped to the tenant.

        Another tenant's row is indistinguishable from a missing one, which is
        what stops ids being used to probe for existence across tenants.
        """
        return await self.find_one(self.model.id == entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        """Persist a new row, forcing it into this repository's tenant.

        The assignment is not a convenience - it overwrites whatever tenant_id
        the caller set, so a value taken from a request body cannot place a row
        in another tenant.
        """
        entity.tenant_id = self.tenant_id
        self.session.add(entity)
        await self.session.flush()
        return entity
