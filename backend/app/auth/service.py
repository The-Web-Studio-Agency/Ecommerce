from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenData,
    UserResponse,
)
from app.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.tenants.repository import TenantRepository
from app.users.repository import UserRepository



class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.tenants = TenantRepository(session)
        self.users = UserRepository(session)

    async def register(
    self,
    data: RegisterRequest,
    ) -> UserResponse:
        tenant = await self.tenants.get_by_slug(
            data.tenant_slug.strip().lower()
        )

        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        email = data.email.strip().lower()

        existing_user = await self.users.get_by_tenant_and_email(
            tenant_id=tenant.id,
            email=email,
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        user = await self.users.create(
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password(data.password),
        )

        await self.session.commit()

        await self.session.refresh(user)

        return UserResponse.model_validate(user)

    async def login(
        self,
        data: LoginRequest,
    ) -> TokenData:
        tenant = await self.tenants.get_by_slug(
            data.tenant_slug.strip().lower()
        )

        # Do not reveal whether the tenant exists.
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        user = await self.users.get_by_tenant_and_email(
            tenant_id=tenant.id,
            email=data.email.strip().lower(),
        )

        # Do not reveal whether the user exists.
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not verify_password(
            data.password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        access_token = create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            role=user.role,
        )

        return TokenData(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )