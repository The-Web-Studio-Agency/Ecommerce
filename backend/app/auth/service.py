"""Authentication business logic.

The service owns the business transaction: repositories flush, the service
commits. It raises `AppError` subclasses, never HTTP exceptions - translating
those into the error envelope is the API layer's job.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import UserRole
from app.auth.schemas import (
    AuthSession,
    LoginRequest,
    RegisterRequest,
    TokenPair,
    UserResponse,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    spend_dummy_verification,
    verify_password,
)
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository
from app.users.models import User
from app.users.repository import UserRepository

logger = get_logger("auth")


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tenants = TenantRepository(session)
        self.users = UserRepository(session)

    # ------------------------------------------------------------- register

    async def register(self, data: RegisterRequest) -> UserResponse:
        tenant = await self.tenants.get_active_by_slug(data.tenant_slug.strip().lower())
        if tenant is None:
            raise NotFoundError("Tenant not found")

        email = data.email.strip().lower()

        if await self.users.get_by_tenant_and_email(tenant_id=tenant.id, email=email) is not None:
            raise ConflictError("An account with this email already exists")

        # Self-registration always creates a CUSTOMER. The role is never taken
        # from the request payload, so it cannot be escalated by the caller.
        try:
            user = await self.users.create(
                tenant_id=tenant.id,
                email=email,
                password_hash=await hash_password(data.password),
                role=UserRole.CUSTOMER.value,
            )
            await self.session.commit()
        except IntegrityError as exc:
            # Two concurrent registrations both pass the check above; the
            # composite unique index is what actually settles it. Without this,
            # the loser of the race gets a 500 instead of a 409.
            await self.session.rollback()
            raise ConflictError("An account with this email already exists") from exc

        logger.info("auth.registered user_id=%s tenant_id=%s", user.id, tenant.id)
        return UserResponse.model_validate(user)

    # ---------------------------------------------------------------- login

    async def login(self, data: LoginRequest) -> AuthSession:
        tenant = await self.tenants.get_active_by_slug(data.tenant_slug.strip().lower())

        # Unknown tenant, unknown user, inactive user and wrong password all
        # return the same error. Each failure path also spends comparable CPU,
        # so neither the response body nor its latency reveals which one hit.
        if tenant is None:
            await spend_dummy_verification()
            raise AuthenticationError("Invalid credentials")

        user = await self.users.get_by_tenant_and_email(
            tenant_id=tenant.id,
            email=data.email.strip().lower(),
        )
        if user is None or not user.is_active:
            await spend_dummy_verification()
            raise AuthenticationError("Invalid credentials")

        if not await verify_password(data.password, user.password_hash):
            logger.info("auth.login_failed user_id=%s tenant_id=%s", user.id, tenant.id)
            raise AuthenticationError("Invalid credentials")

        logger.info("auth.login user_id=%s tenant_id=%s", user.id, tenant.id)
        return self._issue_session(user)

    # -------------------------------------------------------------- refresh

    async def refresh(self, refresh_token: str) -> AuthSession:
        """Exchange a valid refresh token for a new token pair."""
        payload = decode_token(refresh_token, expected_type="refresh")

        try:
            user_id = UUID(payload.subject)
        except ValueError as exc:
            raise AuthenticationError("Invalid authentication token") from exc

        loaded = await self.users.get_with_tenant(user_id)
        if loaded is None:
            raise AuthenticationError("Invalid authentication token")

        user, tenant = loaded
        if not self._is_usable(user, tenant):
            logger.warning("auth.refresh_rejected user_id=%s", user_id)
            raise AuthenticationError("Invalid authentication token")

        return self._issue_session(user)

    # --------------------------------------------------------------- shared

    @staticmethod
    def _is_usable(user: User, tenant: Tenant | None) -> bool:
        """A principal is usable only while both it and its tenant are active."""
        if not user.is_active:
            return False
        # Platform users have no tenant; everyone else needs an active one.
        return user.tenant_id is None or (tenant is not None and tenant.is_active)

    @staticmethod
    def _issue_session(user: User) -> AuthSession:
        settings = get_settings()
        subject = str(user.id)
        tenant_id = str(user.tenant_id) if user.tenant_id else None

        return AuthSession(
            tokens=TokenPair(
                access_token=create_access_token(
                    subject=subject, role=user.role, tenant_id=tenant_id
                ),
                refresh_token=create_refresh_token(
                    subject=subject, role=user.role, tenant_id=tenant_id
                ),
                expires_in=settings.access_token_expire_minutes * 60,
            ),
            user=UserResponse.model_validate(user),
        )
