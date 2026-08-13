from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import (LoginRequest,LoginResponse,RegisterRequest,RegisterResponse)
from app.auth.service import AuthService
from app.core.database import get_db
from app.users.models import User


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    token_data = await AuthService(session).login(data)

    return {
        "success": True,
        "message": "Login successful",
        "data": token_data,
    }

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    user = await AuthService(session).register(data)

    return {
        "success": True,
        "message": "Registration successful",
        "data": user,
    }


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "message": "Authenticated user",
        "data": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
            "tenant_id": current_user.tenant_id,
            "is_active": current_user.is_active,
        },
    }