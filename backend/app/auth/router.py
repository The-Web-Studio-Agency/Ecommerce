"""Authentication routes.

Routes stay thin: resolve dependencies, call the service, wrap the result in the
standard envelope. Errors are raised as `AppError` inside the service and turned
into the error envelope by the handlers in `app.main`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    AuthSession,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
)
from app.auth.service import AuthService
from app.core import rate_limit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.responses import ApiResponse, ok
from app.users.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


def _login_rate_limit_key(request: Request, data: LoginRequest) -> str:
    """Budget logins per (client IP, tenant, account).

    Keying on the account as well as the IP means a distributed attempt against
    one account is still throttled, while one noisy office NAT cannot lock out
    every user behind it.
    """
    client_ip = request.client.host if request.client else "unknown"
    return rate_limit.build_key(
        "login",
        client_ip,
        data.tenant_slug.strip().lower(),
        data.email.strip().lower(),
    )


@router.post(
    "/login",
    response_model=ApiResponse[AuthSession],
    summary="Authenticate and receive an access/refresh token pair",
)
async def login(
    request: Request,
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[AuthSession]:
    settings = get_settings()
    key = _login_rate_limit_key(request, data)

    await rate_limit.hit(
        key,
        limit=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )

    result = await AuthService(session).login(data)
    await rate_limit.reset(key)
    return ok(result, message="Login successful")


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a customer account within a tenant",
)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[UserResponse]:
    user = await AuthService(session).register(data)
    return ok(user, message="Registration successful")


@router.post(
    "/refresh",
    response_model=ApiResponse[AuthSession],
    summary="Exchange a refresh token for a new token pair",
)
async def refresh(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[AuthSession]:
    result = await AuthService(session).refresh(data.refresh_token)
    return ok(result, message="Token refreshed successfully")


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="The authenticated user",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    return ok(UserResponse.model_validate(current_user), message="Authenticated user")
