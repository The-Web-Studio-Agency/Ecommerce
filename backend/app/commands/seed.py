"""Seed the local development database with a tenant and its admin user.

Idempotent: running it repeatedly leaves exactly one tenant and one admin.
"""

from __future__ import annotations

import asyncio

from app.auth.constants import UserRole
from app.auth.security import hash_password
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, dispose_engine
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository
from app.users.repository import UserRepository


async def seed() -> None:
    settings = get_settings()

    if not settings.seed_admin_email:
        raise RuntimeError("SEED_ADMIN_EMAIL is not configured")
    if not settings.seed_admin_password:
        raise RuntimeError("SEED_ADMIN_PASSWORD is not configured")

    slug = settings.seed_tenant_slug.strip().lower()

    async with AsyncSessionLocal() as session:
        tenants = TenantRepository(session)
        users = UserRepository(session)

        tenant = await tenants.get_active_by_slug(slug)
        if tenant is None:
            tenant = Tenant(name=settings.seed_tenant_name, slug=slug, is_active=True)
            session.add(tenant)
            await session.flush()
            print(f"Created tenant: {tenant.name} ({tenant.slug})")
        else:
            print(f"Tenant already exists: {tenant.name} ({tenant.slug})")

        email = settings.seed_admin_email.strip().lower()

        if await users.get_by_tenant_and_email(tenant_id=tenant.id, email=email) is None:
            await users.create(
                tenant_id=tenant.id,
                email=email,
                password_hash=await hash_password(settings.seed_admin_password),
                role=UserRole.TENANT_ADMIN.value,
            )
            print(f"Created tenant admin: {email}")
        else:
            print(f"Tenant admin already exists: {email}")

        await session.commit()

    await dispose_engine()
    print("Seed completed successfully.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
