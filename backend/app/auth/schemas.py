from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    tenant_slug: str = Field(
        min_length=1,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: str
    tenant_id: UUID | None
    is_active: bool


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginResponse(BaseModel):
    success: bool = True
    message: str
    data: TokenData


class RegisterRequest(BaseModel):
    tenant_slug: str = Field(
        min_length=1,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=256,
    )

class RegisterResponse(BaseModel):
    success: bool = True
    message: str
    data: UserResponse