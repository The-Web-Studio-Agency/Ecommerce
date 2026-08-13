from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.tenants.context import TenantContext
from app.tenants.repository import TenantRepository


async def get_tenant_context(
    x_tenant_slug: str | None = Header(
        default=None,
        alias="X-Tenant-Slug",
    ),
    session: AsyncSession = Depends(get_db),
) -> TenantContext:
    """
    Resolve the tenant for the current request.

    X-Tenant-Slug is intentionally used for local development and
    API testing. Production should resolve the tenant from the
    authenticated host/domain at the edge/application boundary.
    """

    if not x_tenant_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context is required",
        )

    slug = x_tenant_slug.strip().lower()

    if not slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context is required",
        )

    tenant = await TenantRepository(session).get_by_slug(slug)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return TenantContext(
        tenant_id=tenant.id,
    )