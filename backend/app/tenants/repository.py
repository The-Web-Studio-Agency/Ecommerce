"""Tenant data access.

Tenants are the boundary itself, not tenant-owned data, so this extends
`BaseRepository` rather than `TenantScopedRepository`.
"""

from __future__ import annotations

from uuid import UUID

from app.core.repository import BaseRepository
from app.tenants.models import Tenant


class TenantRepository(BaseRepository[Tenant]):
    model = Tenant

    async def get_active_by_id(self, tenant_id: UUID) -> Tenant | None:
        return await self.find_one(Tenant.id == tenant_id, Tenant.is_active.is_(True))

    async def get_active_by_slug(self, slug: str) -> Tenant | None:
        return await self.find_one(Tenant.slug == slug, Tenant.is_active.is_(True))
