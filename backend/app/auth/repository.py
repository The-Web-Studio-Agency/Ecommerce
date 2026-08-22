from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AdminAuthChallenge, OtpRequest, RefreshToken


class OtpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        tenant_id: UUID,
        phone: str,
        purpose: str,
        otp_hash: str,
        expires_at: datetime,
        user_id: UUID | None = None,
    ) -> OtpRequest:
        request = OtpRequest(
            tenant_id=tenant_id,
            user_id=user_id,
            phone=phone,
            purpose=purpose,
            otp_hash=otp_hash,
            expires_at=expires_at,
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def expire_active(self, *, tenant_id: UUID, phone: str, purpose: str) -> None:
        await self.session.execute(
            update(OtpRequest)
            .where(
                OtpRequest.tenant_id == tenant_id,
                OtpRequest.phone == phone,
                OtpRequest.purpose == purpose,
                OtpRequest.verified_at.is_(None),
                OtpRequest.expires_at > datetime.now(timezone.utc),
            )
            .values(expires_at=datetime.now(timezone.utc))
        )
        await self.session.flush()

    async def get_by_id(self, *, tenant_id: UUID, otp_id: UUID) -> OtpRequest | None:
        return await self.session.scalar(
            select(OtpRequest).where(
                OtpRequest.id == otp_id, OtpRequest.tenant_id == tenant_id
            )
        )

    async def get_latest(
        self, *, tenant_id: UUID, phone: str, purpose: str
    ) -> OtpRequest | None:
        return await self.session.scalar(
            select(OtpRequest)
            .where(
                OtpRequest.tenant_id == tenant_id,
                OtpRequest.phone == phone,
                OtpRequest.purpose == purpose,
            )
            .order_by(OtpRequest.created_at.desc())
            .limit(1)
        )


class AdminChallengeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        otp_request_id: UUID,
        expires_at: datetime,
    ) -> AdminAuthChallenge:
        challenge = AdminAuthChallenge(
            tenant_id=tenant_id,
            user_id=user_id,
            otp_request_id=otp_request_id,
            expires_at=expires_at,
        )
        self.session.add(challenge)
        await self.session.flush()
        return challenge

    async def get_pending(
        self, *, tenant_id: UUID, challenge_id: UUID
    ) -> AdminAuthChallenge | None:
        return await self.session.scalar(
            select(AdminAuthChallenge).where(
                AdminAuthChallenge.id == challenge_id,
                AdminAuthChallenge.tenant_id == tenant_id,
                AdminAuthChallenge.verified_at.is_(None),
                AdminAuthChallenge.expires_at > datetime.now(timezone.utc),
            )
        )

    async def expire_pending_for_user(self, *, tenant_id: UUID, user_id: UUID) -> None:
        await self.session.execute(
            update(AdminAuthChallenge)
            .where(
                AdminAuthChallenge.tenant_id == tenant_id,
                AdminAuthChallenge.user_id == user_id,
                AdminAuthChallenge.verified_at.is_(None),
                AdminAuthChallenge.expires_at > datetime.now(timezone.utc),
            )
            .values(expires_at=datetime.now(timezone.utc))
        )
        await self.session.flush()

    async def consume(self, challenge: AdminAuthChallenge) -> None:
        challenge.verified_at = datetime.now(timezone.utc)
        await self.session.flush()


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            tenant_id=tenant_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, *, tenant_id: UUID, token_hash: str) -> RefreshToken | None:
        return await self.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.tenant_id == tenant_id,
            )
        )

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.session.flush()
        return int(result.rowcount or 0)
