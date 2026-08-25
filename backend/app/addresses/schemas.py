from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.addresses.models import (
    MAX_CITY_LENGTH,
    MAX_LINE_LENGTH,
    MAX_NAME_LENGTH,
    MAX_POSTAL_CODE_LENGTH,
)
from app.auth.schemas import NormalizedPhone


def _reject_blank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Must not be blank")
    return stripped


def _reject_blank_optional(value: str | None) -> str | None:
    return None if value is None else _reject_blank(value)


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class AddressCreate(BaseModel):
    full_name: str = Field(max_length=MAX_NAME_LENGTH)
    phone: NormalizedPhone
    address_line_1: str = Field(max_length=MAX_LINE_LENGTH)
    address_line_2: str | None = Field(default=None, max_length=MAX_LINE_LENGTH)
    city: str = Field(max_length=MAX_CITY_LENGTH)
    state: str = Field(max_length=MAX_CITY_LENGTH)
    postal_code: str = Field(max_length=MAX_POSTAL_CODE_LENGTH)
    country: str = Field(max_length=MAX_CITY_LENGTH)
    is_default: bool = False

    _strip_full_name = field_validator("full_name")(_reject_blank)
    _strip_line_1 = field_validator("address_line_1")(_reject_blank)
    _strip_line_2 = field_validator("address_line_2")(_strip_optional)
    _strip_city = field_validator("city")(_reject_blank)
    _strip_state = field_validator("state")(_reject_blank)
    _strip_postal_code = field_validator("postal_code")(_reject_blank)
    _strip_country = field_validator("country")(_reject_blank)


class AddressUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    phone: NormalizedPhone | None = None
    address_line_1: str | None = Field(default=None, max_length=MAX_LINE_LENGTH)
    address_line_2: str | None = Field(default=None, max_length=MAX_LINE_LENGTH)
    city: str | None = Field(default=None, max_length=MAX_CITY_LENGTH)
    state: str | None = Field(default=None, max_length=MAX_CITY_LENGTH)
    postal_code: str | None = Field(default=None, max_length=MAX_POSTAL_CODE_LENGTH)
    country: str | None = Field(default=None, max_length=MAX_CITY_LENGTH)
    is_default: bool | None = None

    _strip_full_name = field_validator("full_name")(_reject_blank_optional)
    _strip_line_1 = field_validator("address_line_1")(_reject_blank_optional)
    _strip_line_2 = field_validator("address_line_2")(_strip_optional)
    _strip_city = field_validator("city")(_reject_blank_optional)
    _strip_state = field_validator("state")(_reject_blank_optional)
    _strip_postal_code = field_validator("postal_code")(_reject_blank_optional)
    _strip_country = field_validator("country")(_reject_blank_optional)


class AddressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    phone: str
    address_line_1: str
    address_line_2: str | None
    city: str
    state: str
    postal_code: str
    country: str
    is_default: bool
