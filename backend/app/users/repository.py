"""User data access.

Users are looked up by (tenant, email) rather than by email alone: the same
address may legitimately exist in several tenants, and the composite unique
index `uq_users_tenant_email` is what makes that lookup exact.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.auth.constants import UserRole
from app.core.repository import BaseRepository
from app.tenants.models import Tenant
from app.users.models import User


class UserRepository(BaseRepository[User]):
    model = User

    async def create(
        self,
        *,
        tenant_id: UUID | None,
        email: str,
        password_hash: str,
        role: str = UserRole.CUSTOMER.value,
    ) -> User:
        return await self.add(
            User(
                tenant_id=tenant_id,
                email=email,
                password_hash=password_hash,
                role=role,
                is_active=True,
            )
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.find_one(User.id == user_id)

    async def get_by_tenant_and_email(self, tenant_id: UUID, email: str) -> User | None:
        return await self.find_one(User.tenant_id == tenant_id, User.email == email)

    async def get_with_tenant(self, user_id: UUID) -> tuple[User, Tenant | None] | None:
        """Load a user and its tenant in ONE round trip.

        Authentication needs both on every request (the user must be active and
        so must their tenant); an outer join keeps that at a single query rather
        than two, since this runs on the hot path for every authenticated call.
        """
        statement = (
            select(User, Tenant)
            .outerjoin(Tenant, User.tenant_id == Tenant.id)
            .where(User.id == user_id)
        )
        row = (await self.session.execute(statement)).first()
        if row is None:
            return None
        return row[0], row[1]
