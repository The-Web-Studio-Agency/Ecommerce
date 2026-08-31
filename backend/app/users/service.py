from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import UserRole
from app.auth.phone import normalize_phone
from app.auth.security import hash_password
from app.users.models import User
from app.users.repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def create(
        self,
        *,
        role: UserRole,
        tenant_id: UUID,
        email: str,
        phone: str,
        password: str,
        name: str | None = None,
    ) -> tuple[User, bool]:
        """Create the tenant's user if absent; returns the user and whether it was created."""
        email = email.strip().lower()
        phone = normalize_phone(phone)

        existing = await self.users.get_by_email(tenant_id=tenant_id, email=email)
        if existing is not None:
            return existing, False

        existing = await self.users.get_by_phone(tenant_id=tenant_id, phone=phone)
        if existing is not None:
            return existing, False

        password_hash = (
            None if role is UserRole.CUSTOMER else await hash_password(password)
        )

        user = await self.users.create(
            tenant_id=tenant_id,
            phone=phone,
            email=email,
            name=name,
            role=role.value,
            password_hash=password_hash,
            is_verified=True,
        )
        await self.session.commit()
        return user, True
