from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.catalogue.constants import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    MAX_SKU_LENGTH,
    MAX_SLUG_LENGTH,
    PRICE_SCALE,
    CatalogueStatus,
)

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
SKU_PATTERN = r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$"

Name = Field(min_length=1, max_length=MAX_NAME_LENGTH)
Slug = Field(min_length=1, max_length=MAX_SLUG_LENGTH, pattern=SLUG_PATTERN)
Sku = Field(min_length=1, max_length=MAX_SKU_LENGTH, pattern=SKU_PATTERN)
Description = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
Price = Field(ge=0, max_digits=10, decimal_places=PRICE_SCALE)


def _reject_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value.strip()


class CategoryCreate(BaseModel):
    name: str = Name
    slug: str = Slug
    description: str | None = Description
    is_active: bool = True

    _strip_name = field_validator("name")(_reject_blank)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    slug: str | None = Field(
        default=None, min_length=1, max_length=MAX_SLUG_LENGTH, pattern=SLUG_PATTERN
    )
    description: str | None = Description
    is_active: bool | None = None

    _strip_name = field_validator("name")(lambda v: v if v is None else _reject_blank(v))


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: str | None
    is_active: bool


class ProductCreate(BaseModel):
    category_id: UUID
    name: str = Name
    slug: str = Slug
    description: str | None = Description
    status: CatalogueStatus = CatalogueStatus.DRAFT

    _strip_name = field_validator("name")(_reject_blank)


class ProductUpdate(BaseModel):
    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    slug: str | None = Field(
        default=None, min_length=1, max_length=MAX_SLUG_LENGTH, pattern=SLUG_PATTERN
    )
    description: str | None = Description
    status: CatalogueStatus | None = None

    _strip_name = field_validator("name")(lambda v: v if v is None else _reject_blank(v))


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    category_id: UUID
    name: str
    slug: str
    description: str | None
    status: CatalogueStatus


class VariantCreate(BaseModel):
    sku: str = Sku
    name: str = Name
    price: Decimal = Price
    status: CatalogueStatus = CatalogueStatus.DRAFT

    _strip_name = field_validator("name")(_reject_blank)


class VariantUpdate(BaseModel):
    sku: str | None = Field(
        default=None, min_length=1, max_length=MAX_SKU_LENGTH, pattern=SKU_PATTERN
    )
    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=PRICE_SCALE)
    status: CatalogueStatus | None = None

    _strip_name = field_validator("name")(lambda v: v if v is None else _reject_blank(v))


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_id: UUID
    sku: str
    name: str
    price: Decimal
    status: CatalogueStatus
