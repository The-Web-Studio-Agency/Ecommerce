from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import ApiResponse, ok
from app.tenants.resolver import resolve_tenant_optional
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository
from app.users.schemas import UserCreate, UserRead
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/admin",
    response_model=ApiResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create an admin user",
)
async def create_admin(
    data: UserCreate,
    tenant: Tenant | None = Depends(resolve_tenant_optional),
    tenant_id: str | None = Query(None, description="Tenant id for local testing"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[UserRead]:
    # Allow optional tenant_id for local testing (localhost). If tenant resolver
    # did not produce a tenant, fall back to provided tenant_id or the first
    # active tenant in the DB.
    if tenant is None:
        repo = TenantRepository(session)
        if tenant_id:
            tenant = await repo.get_active_by_id(tenant_id)
        else:
            # Pick the first active tenant available.
            # This is safe for local development only.
            from app.tenants.models import Tenant
            from sqlalchemy import select

            tenant = await session.scalar(select(Tenant).where(Tenant.is_active.is_(True)))

    svc = UserService(session)
    user_obj, created = await svc.create_admin(
        tenant_id=tenant.id,
        email=data.email,
        phone=data.phone,
        name=data.name,
        password=data.password,
    )
    user_data = {
        "id": user_obj.id,
        "tenant_id": user_obj.tenant_id,
        "email": user_obj.email,
        "phone": user_obj.phone,
        "name": user_obj.name,
        "role": user_obj.role,
        "status": user_obj.status,
        "is_verified": user_obj.is_verified,
    }
    return ok(UserRead.model_validate(user_data), message=("Admin created" if created else "Admin exists"))


@router.post(
    "/staff",
    response_model=ApiResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff user",
)
async def create_staff(
    data: UserCreate,
    tenant: Tenant | None = Depends(resolve_tenant_optional),
    tenant_id: str | None = Query(None, description="Tenant id for local testing"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[UserRead]:
    if tenant is None:
        repo = TenantRepository(session)
        if tenant_id:
            tenant = await repo.get_active_by_id(tenant_id)
        else:
            from app.tenants.models import Tenant
            from sqlalchemy import select

            tenant = await session.scalar(select(Tenant).where(Tenant.is_active.is_(True)))

    svc = UserService(session)
    user_obj, created = await svc.create_staff(
        tenant_id=tenant.id,
        email=data.email,
        phone=data.phone,
        name=data.name,
        password=data.password,
    )
    user_data = {
        "id": user_obj.id,
        "tenant_id": user_obj.tenant_id,
        "email": user_obj.email,
        "phone": user_obj.phone,
        "name": user_obj.name,
        "role": user_obj.role,
        "status": user_obj.status,
        "is_verified": user_obj.is_verified,
    }
    return ok(UserRead.model_validate(user_data), message=("Staff created" if created else "Staff exists"))
