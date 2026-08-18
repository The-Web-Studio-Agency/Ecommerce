from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.phone import normalize_phone
from app.auth.security import hash_password
from app.auth.constants import UserRole
from app.users.repository import UserRepository
from app.users.models import User


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def create_admin(
        self,
        *,
        tenant_id: UUID,
        email: str,
        phone: str,
        name: Optional[str] = None,
        password: str,
    ) -> tuple[User, bool]:
        """Create an admin user if one does not already exist.

        Returns the existing or newly-created `User`.
        """
        email = email.strip().lower()
        phone = normalize_phone(phone)

        existing = await self.users.get_by_email(tenant_id=tenant_id, email=email)
        if existing is not None:
            return existing, False

        password_hash = await hash_password(password)
        user = await self.users.create(
            tenant_id=tenant_id,
            phone=phone,
            email=email,
            name=name,
            role=UserRole.ADMIN.value,
            password_hash=password_hash,
            is_verified=True,
        )
        await self.session.commit()
        return user, True

    async def create_staff(
        self,
        *,
        tenant_id: UUID,
        email: str,
        phone: str,
        name: Optional[str] = None,
        password: str,
    ) -> tuple[User, bool]:
        """Create a staff user if one does not already exist.

        Returns the existing or newly-created `User`.
        """
        email = email.strip().lower()
        phone = normalize_phone(phone)

        existing = await self.users.get_by_email(tenant_id=tenant_id, email=email)
        if existing is not None:
            return existing, False

        password_hash = await hash_password(password)
        user = await self.users.create(
            tenant_id=tenant_id,
            phone=phone,
            email=email,
            name=name,
            role=UserRole.STAFF.value,
            password_hash=password_hash,
            is_verified=True,
        )
        await self.session.commit()
        return user, True
