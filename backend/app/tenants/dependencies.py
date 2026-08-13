"""Public (unauthenticated) tenant resolution.

Storefront traffic carries no credentials, so the tenant is resolved from the
request itself. Back-office traffic must NOT use this - it takes the tenant from
the authenticated user via `app.auth.dependencies.get_authenticated_tenant`, so
a header can never widen an authenticated caller's scope.
"""

from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, TenantContextError
from app.core.tenant_context import TenantContext
from app.tenants.repository import TenantRepository


async def get_public_tenant_context(
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    session: AsyncSession = Depends(get_db),
) -> TenantContext:
    """Resolve the tenant for a public request from `X-Tenant-Slug`.

    Production should additionally resolve the tenant from the request host at
    the edge; the header remains the explicit override for local development and
    API testing.
    """
    slug = (x_tenant_slug or "").strip().lower()
    if not slug:
        raise TenantContextError("Tenant context is required")

    tenant = await TenantRepository(session).get_active_by_slug(slug)
    if tenant is None:
        # Inactive and non-existent tenants are reported identically so the
        # header cannot be used to enumerate tenants.
        raise NotFoundError("Tenant not found")

    return TenantContext(tenant_id=tenant.id, slug=tenant.slug, name=tenant.name)
