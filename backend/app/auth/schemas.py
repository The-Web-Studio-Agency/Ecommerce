from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.auth.constants import OTP_LENGTH
from app.auth.phone import normalize_phone

MAX_PASSWORD_LENGTH = 256
MIN_PASSWORD_LENGTH = 8

NormalizedPhone = Annotated[
    str,
    Field(min_length=4, max_length=32),
    AfterValidator(normalize_phone),
]

OtpCode = Annotated[str, Field(min_length=OTP_LENGTH, max_length=OTP_LENGTH, pattern=r"^\d+$")]


class OtpRequestPayload(BaseModel):
    phone: NormalizedPhone


class OtpVerifyPayload(BaseModel):
    phone: NormalizedPhone
    otp: OtpCode


class PasswordLoginPayload(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class StaffOtpVerifyPayload(BaseModel):
    verification_id: UUID
    otp: OtpCode


class StaffLoginChallenge(BaseModel):
    verification_id: UUID


class RefreshPayload(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutPayload(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    phone: str
    email: EmailStr | None
    name: str | None
    role: str
    status: str
    is_verified: bool


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_active: bool
