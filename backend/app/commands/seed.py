import asyncio

from sqlalchemy import select

from app.auth.constants import UserRole
from app.auth.security import hash_password
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.tenants.models import Tenant
from app.users.models import User


TENANT_NAME = "Zeen"
TENANT_SLUG = "zeen"


async def seed() -> None:
    if not settings.seed_admin_email:
        raise RuntimeError(
            "SEED_ADMIN_EMAIL is not configured"
        )

    if not settings.seed_admin_password:
        raise RuntimeError(
            "SEED_ADMIN_PASSWORD is not configured"
        )

    async with AsyncSessionLocal() as session:
        # ---------------------------------------------------------
        # Tenant
        # ---------------------------------------------------------

        result = await session.execute(
            select(Tenant).where(
                Tenant.slug == TENANT_SLUG
            )
        )

        tenant = result.scalar_one_or_none()

        if tenant is None:
            tenant = Tenant(
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                is_active=True,
            )

            session.add(tenant)

            await session.flush()

            print(
                f"Created tenant: {tenant.name} "
                f"({tenant.slug})"
            )

        else:
            print(
                f"Tenant already exists: "
                f"{tenant.name} ({tenant.slug})"
            )

        # ---------------------------------------------------------
        # Admin user
        # ---------------------------------------------------------

        email = settings.seed_admin_email.strip().lower()

        result = await session.execute(
            select(User).where(
                User.tenant_id == tenant.id,
                User.email == email,
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=hash_password(
                    settings.seed_admin_password
                ),
                role=UserRole.TENANT_ADMIN.value,
                is_active=True,
            )

            session.add(user)

            print(
                f"Created tenant admin: {email}"
            )

        else:
            print(
                f"Tenant admin already exists: {email}"
            )

        await session.commit()

        print("Seed completed successfully.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()