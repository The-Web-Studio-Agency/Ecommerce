from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User
from app.auth.constants import UserRole


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        tenant_id,
        email: str,
        password_hash: str,
        role: str = UserRole.CUSTOMER.value,
         ) -> User:
        user = User(
            tenant_id=tenant_id,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )

        self.session.add(user)

        await self.session.flush()

        return user

    async def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        result = await self.session.execute(
            select(User).where(
                User.id == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_tenant_and_email(
        self,
        tenant_id: UUID,
        email: str,
    ) -> User | None:
        result = await self.session.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.email == email,
            )
        )

        return result.scalar_one_or_none()

