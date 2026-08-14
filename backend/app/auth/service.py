"""Authentication business logic.

The service owns the business transaction: repositories flush, the service
commits. It raises `AppError` subclasses, never HTTP exceptions - translating
those into the error envelope is the API layer's job.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import UserRole
from app.auth.repository import RefreshTokenRepository
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
    hash_refresh_token,
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
        self.refresh_tokens = RefreshTokenRepository(session)

    # ------------------------------------------------------------- register

    async def register(self, data: RegisterRequest) -> UserResponse:
        tenant = await self.tenants.get_active_by_slug(data.tenant_slug.strip().lower())
        if tenant is None:
            raise NotFoundError("Tenant not found")

        email = data.email.strip().lower()

        if await self.users.get_by_tenant_and_email(tenant_id=tenant.id, email=email) is not None:
            raise ConflictError("An account with this email already exists")

       
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

        session = await self._issue_session(user)
        await self.session.commit()

        logger.info("auth.login user_id=%s tenant_id=%s", user.id, tenant.id)
        return session

    # -------------------------------------------------------------- refresh

    async def refresh(self, refresh_token: str) -> AuthSession:
        """Rotate a refresh token: the presented token is spent, a new pair issued.

        Rotation is what makes a stolen refresh token detectable. Because each
        token may be redeemed exactly once, a replay of an already-rotated
        token means two parties hold it, and every session for that user is cut.
        """
        stored, user = await self._resolve_refresh_token(refresh_token)

        # Reuse: this token was already rotated (or explicitly logged out).
        # Either the legitimate client replayed it or an attacker did, and we
        # cannot tell which - so end every session and force a fresh login.
        if stored.revoked_at is not None:
            revoked = await self.refresh_tokens.revoke_all_for_user(stored.user_id)
            await self.session.commit()
            logger.warning(
                "auth.refresh_reuse_detected user_id=%s sessions_revoked=%s",
                stored.user_id,
                revoked,
            )
            raise AuthenticationError("Invalid authentication token")

        if stored.expires_at <= datetime.now(timezone.utc):
            raise AuthenticationError("Invalid authentication token")

        await self.refresh_tokens.revoke(stored)
        session = await self._issue_session(user)
        await self.session.commit()

        logger.info("auth.refreshed user_id=%s", user.id)
        return session

    # --------------------------------------------------------------- logout

    async def logout(self, refresh_token: str) -> None:
        """Revoke the presented refresh token.

        Deliberately silent about tokens that are unknown, expired or already
        revoked: logout must not become an oracle for which tokens are valid,
        and a client retrying a logout should not receive an error.
        """
        stored = await self.refresh_tokens.get_by_hash(hash_refresh_token(refresh_token))
        if stored is not None and stored.revoked_at is None:
            await self.refresh_tokens.revoke(stored)
            logger.info("auth.logout user_id=%s", stored.user_id)

        await self.session.commit()

    # --------------------------------------------------------------- shared

    async def _resolve_refresh_token(self, refresh_token: str) -> tuple:
        """Validate a refresh token's signature, its row, and its principal."""
        payload = decode_token(refresh_token, expected_type="refresh")

        try:
            user_id = UUID(payload.subject)
        except ValueError as exc:
            raise AuthenticationError("Invalid authentication token") from exc

        stored = await self.refresh_tokens.get_by_hash(hash_refresh_token(refresh_token))
        if stored is None or stored.user_id != user_id:
            # A validly signed token with no row was issued before a revocation
            # sweep, or never issued by us at all.
            raise AuthenticationError("Invalid authentication token")

        loaded = await self.users.get_with_tenant(user_id)
        if loaded is None:
            raise AuthenticationError("Invalid authentication token")

        user, tenant = loaded
        if not self._is_usable(user, tenant):
            logger.warning("auth.refresh_rejected user_id=%s", user_id)
            raise AuthenticationError("Invalid authentication token")

        return stored, user

    @staticmethod
    def _is_usable(user: User, tenant: Tenant | None) -> bool:
        """A principal is usable only while both it and its tenant are active."""
        if not user.is_active:
            return False
        # Platform users have no tenant; everyone else needs an active one.
        return user.tenant_id is None or (tenant is not None and tenant.is_active)

    async def _issue_session(self, user: User) -> AuthSession:
        """Mint an access/refresh pair and record the refresh token.

        Does not commit - the caller owns the transaction.
        """
        settings = get_settings()
        subject = str(user.id)
        tenant_id = str(user.tenant_id) if user.tenant_id else None

        access_token = create_access_token(
            subject=subject, role=user.role, tenant_id=tenant_id
        )
        refresh_token = create_refresh_token(
            subject=subject, role=user.role, tenant_id=tenant_id
        )

        await self.refresh_tokens.add(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )

        return AuthSession(
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.access_token_expire_minutes * 60,
            ),
            user=UserResponse.model_validate(user),
        )
