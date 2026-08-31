from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.auth.schemas import (
    LogoutPayload,
    OtpRequestPayload,
    OtpVerifyPayload,
    PasswordLoginPayload,
    RefreshPayload,
    StaffOtpVerifyPayload,
    TenantResponse,
    TokenPair,
    UserProfile,
)
from app.auth.security import hash_refresh_token
from app.auth.service import AuthService
from app.core import rate_limit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.request_context import client_ip
from app.core.responses import ApiResponse, ok
from app.tenants.models import Tenant
from app.tenants.resolver import CurrentTenant

router = APIRouter(prefix="/auth", tags=["Auth"])
admin_router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])
staff_router = APIRouter(prefix="/staff/auth", tags=["Staff Auth"])


async def _throttle(
    request: Request,
    tenant: Tenant,
    scope: str,
    subject: str,
    *,
    limit: int,
    window_seconds: int,
) -> str:
    settings = get_settings()
    ip = client_ip(request)

    await rate_limit.hit(
        rate_limit.build_key(f"{scope}-ip", ip, str(tenant.id)),
        limit=settings.otp_ip_rate_limit_attempts,
        window_seconds=window_seconds,
    )

    subject_key = rate_limit.build_key(scope, ip, str(tenant.id), subject)
    await rate_limit.hit(subject_key, limit=limit, window_seconds=window_seconds)
    return subject_key


@router.post(
    "/otp/request",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[None],
    summary="Send a login code to a customer's phone",
)
async def request_otp(
    request: Request,
    data: OtpRequestPayload,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    settings = get_settings()
    await _throttle(
        request,
        tenant,
        "otp-request",
        data.phone,
        limit=settings.otp_request_rate_limit_attempts,
        window_seconds=settings.otp_rate_limit_window_seconds,
    )

    await AuthService(session, tenant).request_customer_otp(data.phone)
    return ok(message="OTP sent")


@router.post(
    "/otp/verify",
    response_model=ApiResponse[TokenPair],
    summary="Verify a customer's code and receive a token pair",
)
async def verify_otp(
    request: Request,
    data: OtpVerifyPayload,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenPair]:
    settings = get_settings()
    key = await _throttle(
        request,
        tenant,
        "otp-verify",
        data.phone,
        limit=settings.otp_verify_rate_limit_attempts,
        window_seconds=settings.otp_rate_limit_window_seconds,
    )

    tokens = await AuthService(session, tenant).verify_customer_otp(data.phone, data.otp)

    await rate_limit.reset(key)
    return ok(tokens, message="Login successful")


@admin_router.post(
    "/login",
    response_model=ApiResponse[TokenPair],
    summary="Verify an admin password and receive a token pair",
)
async def admin_login(
    request: Request,
    data: PasswordLoginPayload,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenPair]:
    settings = get_settings()
    key = await _throttle(
        request,
        tenant,
        "admin-login",
        data.identifier.strip().lower(),
        limit=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )

    tokens = await AuthService(session, tenant).admin_login(data.identifier, data.password)

    await rate_limit.reset(key)
    return ok(tokens, message="Login successful")


@staff_router.post(
    "/login",
    response_model=ApiResponse[TokenPair],
    summary="Verify a staff password and receive a token pair",
)
async def staff_login(
    request: Request,
    data: PasswordLoginPayload,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenPair]:
    settings = get_settings()
    key = await _throttle(
        request,
        tenant,
        "staff-login",
        data.identifier.strip().lower(),
        limit=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )

    tokens = await AuthService(session, tenant).staff_login(data.identifier, data.password)

    await rate_limit.reset(key)
    return ok(tokens, message="Login successful")


async def _verify_staff_otp(
    request: Request,
    data: StaffOtpVerifyPayload,
    tenant: Tenant,
    session: AsyncSession,
) -> ApiResponse[TokenPair]:
    settings = get_settings()
    key = await _throttle(
        request,
        tenant,
        "staff-otp-verify",
        str(data.verification_id),
        limit=settings.otp_verify_rate_limit_attempts,
        window_seconds=settings.otp_rate_limit_window_seconds,
    )

    tokens = await AuthService(session, tenant).verify_staff_otp(
        data.verification_id, data.otp
    )

    await rate_limit.reset(key)
    return ok(tokens, message="Login successful")


@admin_router.post(
    "/verify-otp",
    include_in_schema=False,
    response_model=ApiResponse[TokenPair],
)
async def legacy_admin_verify_otp(
    request: Request,
    data: StaffOtpVerifyPayload,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenPair]:
    return await _verify_staff_otp(request, data, tenant, session)


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenPair],
    summary="Rotate a refresh token for a new token pair",
)
async def refresh(
    request: Request,
    data: RefreshPayload,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenPair]:
    settings = get_settings()
    await _throttle(
        request,
        tenant,
        "refresh",
        hash_refresh_token(data.refresh_token),
        limit=settings.refresh_rate_limit_attempts,
        window_seconds=settings.otp_rate_limit_window_seconds,
    )

    tokens = await AuthService(session, tenant).refresh_tokens(data.refresh_token)
    return ok(tokens, message="Token refreshed successfully")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
)
async def logout(
    data: LogoutPayload,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> Response:
    await AuthService(session, tenant).logout(data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=ApiResponse[UserProfile],
    summary="The authenticated user's profile",
)
async def get_me(current_user: CurrentUser) -> ApiResponse[UserProfile]:
    return ok(UserProfile.model_validate(current_user), message="Authenticated user")


@router.get(
    "/tenants",
    response_model=ApiResponse[list[TenantResponse]],
    summary="List all active tenants",
)
async def list_tenants(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[TenantResponse]]:
    result = await session.execute(
        select(Tenant).where(Tenant.is_active.is_(True)).order_by(Tenant.name)
    )
    tenants = result.scalars().all()
    return ok(
        [TenantResponse.model_validate(t) for t in tenants],
        message="List of active tenants",
    )
