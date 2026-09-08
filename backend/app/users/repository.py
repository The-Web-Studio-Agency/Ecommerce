from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import UserRole, UserStatus
from app.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        tenant_id: UUID,
        phone: str,
        role: str = UserRole.CUSTOMER.value,
        email: str | None = None,
        name: str | None = None,
        password_hash: str | None = None,
        is_verified: bool = False,
    ) -> User:
        user = User(
            tenant_id=tenant_id,
            phone=phone,
            role=role,
            email=email,
            name=name,
            password_hash=password_hash,
            status=UserStatus.ACTIVE.value,
            is_verified=is_verified,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, *, tenant_id: UUID, user_id: UUID) -> User | None:
        return await self.session.scalar(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )

    async def get_by_phone(self, *, tenant_id: UUID, phone: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.tenant_id == tenant_id, User.phone == phone)
        )

    async def get_by_email(self, *, tenant_id: UUID, email: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.tenant_id == tenant_id, User.email == email)
        )
