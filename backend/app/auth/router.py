"""Authentication routes.

Routes stay thin: resolve dependencies, call the service, wrap the result in the
standard envelope. Errors are raised as `AppError` inside the service and turned
into the error envelope by the handlers in `app.main`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    AuthSession,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
)
from app.auth.service import AuthService
from app.core import rate_limit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.responses import ApiResponse, ok
from app.core.request_context import client_ip
from app.users.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


async def _throttle_login(request: Request, data: LoginRequest) -> str:
    """Apply both login budgets. Returns the per-account key for later reset.

    Two counters, because they stop different attacks:
      * per (IP, tenant, account) - brute-forcing one account;
      * per (IP, tenant) - spraying one password across many accounts, which
        the per-account counter cannot see because each account has its own.
    """
    settings = get_settings()
    ip = client_ip(request)
    tenant_slug = data.tenant_slug.strip().lower()

    ip_key = rate_limit.build_key("login-ip", ip, tenant_slug)
    await rate_limit.hit(
        ip_key,
        limit=settings.login_ip_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )

    account_key = rate_limit.build_key("login", ip, tenant_slug, data.email.strip().lower())
    await rate_limit.hit(
        account_key,
        limit=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )
    return account_key


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
    account_key = await _throttle_login(request, data)

    result = await AuthService(session).login(data)

    # Clear only the per-account budget: a successful login proves this account
    # is not under attack, but says nothing about the other accounts this IP
    # may be working through.
    await rate_limit.reset(account_key)
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
    summary="Rotate a refresh token for a new token pair",
)
async def refresh(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[AuthSession]:
    result = await AuthService(session).refresh(data.refresh_token)
    return ok(result, message="Token refreshed successfully")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
)
async def logout(
    data: LogoutRequest,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Always 204, including for unknown or already-revoked tokens.

    Reporting whether the token existed would turn logout into an oracle, and a
    client retrying a logout should not be handed an error.
    """
    await AuthService(session).logout(data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="The authenticated user",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    return ok(UserResponse.model_validate(current_user), message="Authenticated user")
