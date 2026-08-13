"""Request/response schemas for authentication.

Password bounds are deliberately asymmetric: registration enforces the policy
(a minimum length), login only enforces the same MAXIMUM. The maxima must match
- when login capped at 128 while registration allowed 256, any account created
with a longer password could never authenticate again.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

#: Argon2id has no input-length limit of its own, but an unbounded password is
#: an unbounded amount of hashing work, so the request schema caps it.
MAX_PASSWORD_LENGTH = 256
MIN_PASSWORD_LENGTH = 8


class LoginRequest(BaseModel):
    tenant_slug: str = Field(min_length=1, max_length=100)
    email: EmailStr
    # No minimum: login validates credentials, it does not re-apply the policy.
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class RegisterRequest(BaseModel):
    tenant_slug: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: str
    tenant_id: UUID | None
    is_active: bool


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class AuthSession(BaseModel):
    """Login/refresh result: tokens plus who and where you are."""

    tokens: TokenPair
    user: UserResponse
