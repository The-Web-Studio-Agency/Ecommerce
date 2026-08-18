from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tenants.models import Tenant, TenantDomain


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_by_id(self, tenant_id: UUID) -> Tenant | None:
        return await self.session.scalar(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active.is_(True))
        )

    async def get_active_by_slug(self, slug: str) -> Tenant | None:
        return await self.session.scalar(
            select(Tenant).where(Tenant.slug == slug, Tenant.is_active.is_(True))
        )

    async def get_active_by_domain(self, domain: str) -> Tenant | None:
        return await self.session.scalar(
            select(Tenant)
            .join(TenantDomain, TenantDomain.tenant_id == Tenant.id)
            .where(TenantDomain.domain == domain, Tenant.is_active.is_(True))
        )
