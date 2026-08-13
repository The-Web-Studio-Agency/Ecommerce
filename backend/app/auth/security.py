"""Password hashing and JWT issuing/verification.

Hashing runs in a worker thread. Argon2id deliberately costs ~250ms of CPU per
call; running that inline on the asyncio event loop would block every other
in-flight request on the worker for the duration, capping the whole process at
roughly four logins per second. `anyio.to_thread.run_sync` moves the cost onto
the threadpool so only the calling request waits.

Access and refresh tokens are signed with SEPARATE secrets so that a leaked
access-token secret cannot be used to mint refresh tokens. Tokens carry the
tenant id, which the tenant-context dependency validates on every request - the
token is a claim, never the authority, for tenant scoping.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import anyio.to_thread
import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

TokenType = Literal["access", "refresh"]

password_hash = PasswordHash.recommended()

#: Hash of a throwaway password, used to spend comparable CPU time when the
#: account does not exist so that login timing does not reveal which emails are
#: registered. Computed lazily on first use.
_DUMMY_HASH: str | None = None


@dataclass(frozen=True)
class TokenPayload:
    """Decoded, verified JWT claims."""

    subject: str
    token_type: TokenType
    role: str | None
    tenant_id: str | None
    jti: str
    expires_at: datetime


# --------------------------------------------------------------- passwords


def _hash_sync(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def _verify_sync(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(plain_password, hashed_password)
    except (ValueError, TypeError, PwdlibError):
        # A corrupt row, or a hash written by a hasher that is no longer
        # enabled, is a failed login - never a 500 that reveals the stored
        # value is unreadable.
        return False


async def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with Argon2id, off the event loop."""
    return await anyio.to_thread.run_sync(_hash_sync, plain_password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against its stored hash, off the event loop."""
    return await anyio.to_thread.run_sync(_verify_sync, plain_password, hashed_password)


async def spend_dummy_verification() -> None:
    """Burn the same CPU as a real verification for a non-existent account.

    Without this, "no such user" returns in microseconds while a wrong password
    takes ~250ms, which turns response latency into a user-enumeration oracle.
    """
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = await hash_password(uuid.uuid4().hex)
    await verify_password("not-the-password", _DUMMY_HASH)


# ------------------------------------------------------------------ tokens


def _create_token(
    *,
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    secret: str,
    role: str | None,
    tenant_id: str | None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    claims: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "role": role,
        "tid": tenant_id,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(claims, secret, algorithm=settings.jwt_algorithm)


def create_access_token(*, subject: str, role: str | None, tenant_id: str | None) -> str:
    settings = get_settings()
    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        secret=settings.jwt_secret,
        role=role,
        tenant_id=tenant_id,
    )


def create_refresh_token(*, subject: str, role: str | None, tenant_id: str | None) -> str:
    settings = get_settings()
    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        secret=settings.jwt_refresh_secret,
        role=role,
        tenant_id=tenant_id,
    )


def decode_token(token: str, *, expected_type: TokenType) -> TokenPayload:
    """Verify a JWT and return its claims.

    Raises AuthenticationError for expired, malformed, or wrong-type tokens.
    Because each token type is signed with its own secret, a refresh token
    presented as an access token fails signature verification outright.
    """
    settings = get_settings()
    secret = settings.jwt_secret if expected_type == "access" else settings.jwt_refresh_secret
    try:
        claims = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired", error_code="TOKEN_EXPIRED") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid authentication token") from exc

    if claims.get("type") != expected_type:
        raise AuthenticationError("Invalid authentication token")

    subject = claims.get("sub")
    if not subject:
        raise AuthenticationError("Invalid authentication token")

    return TokenPayload(
        subject=str(subject),
        token_type=expected_type,
        role=claims.get("role"),
        tenant_id=claims.get("tid"),
        jti=str(claims.get("jti", "")),
        expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc),
    )
