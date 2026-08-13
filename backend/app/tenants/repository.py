from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tenants.models import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self,
        tenant_id: UUID,
    ) -> Tenant | None:
        result = await self.session.execute(
            select(Tenant).where(
                Tenant.id == tenant_id,
                Tenant.is_active.is_(True),
            )
        )

        return result.scalar_one_or_none()

    async def get_by_slug(
        self,
        slug: str,
    ) -> Tenant | None:
        result = await self.session.execute(
            select(Tenant).where(
                Tenant.slug == slug,
                Tenant.is_active.is_(True),
            )
        )

        return result.scalar_one_or_none()