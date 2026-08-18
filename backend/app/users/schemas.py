from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    phone: str = Field(min_length=6, max_length=32)
    name: str | None = None
    password: str = Field(min_length=8, max_length=256)


class UserRead(BaseModel):
    id: UUID
    tenant_id: UUID
    email: EmailStr | None
    phone: str
    name: str | None
    role: str
    status: str
    is_verified: bool
