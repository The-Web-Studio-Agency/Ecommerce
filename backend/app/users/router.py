from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import ApiResponse, ok
from app.tenants.resolver import CurrentTenant
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
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[UserRead]:
    svc = UserService(session)
    user_obj, created = await svc.create_admin(
        tenant_id=tenant.id,
        email=data.email,
        phone=data.phone,
        name=data.name,
        password=data.password,
    )
    return ok(UserRead.model_validate(user_obj), message=("Admin created" if created else "Admin exists"))


@router.post(
    "/staff",
    response_model=ApiResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff user",
)
async def create_staff(
    data: UserCreate,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[UserRead]:
    svc = UserService(session)
    user_obj, created = await svc.create_staff(
        tenant_id=tenant.id,
        email=data.email,
        phone=data.phone,
        name=data.name,
        password=data.password,
    )
    return ok(UserRead.model_validate(user_obj), message=("Staff created" if created else "Staff exists"))
