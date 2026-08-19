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

# ----Category Schemas--------------------------------------------

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

# -------------------------PRODUCT SCHEMAS--------------------------------------------


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

# ------------------------PRODUCT VARIANT SCHEMAS--------------------------------------------


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

# -----------------------PRODUCT IMAGE SCHEMAS--------------------------------------------   

class ProductImageCreate(BaseModel):
    url: str = Field(
        min_length=1,
        max_length=2048,
    )

    alt_text: str | None = Field(
        default=None,
        max_length=255,
    )

    sort_order: int = Field(
        default=0,
        ge=0,
    )

    is_primary: bool = False

    _strip_url = field_validator("url")(_reject_blank)

    _strip_alt_text = field_validator("alt_text")(
        lambda v: v if v is None else v.strip()
    )


class ProductImageUpdate(BaseModel):
    url: str | None = Field(
        default=None,
        min_length=1,
        max_length=2048,
    )

    alt_text: str | None = Field(
        default=None,
        max_length=255,
    )

    sort_order: int | None = Field(
        default=None,
        ge=0,
    )

    is_primary: bool | None = None

    _strip_url = field_validator("url")(
        lambda v: v if v is None else _reject_blank(v)
    )

    _strip_alt_text = field_validator("alt_text")(
        lambda v: v if v is None else v.strip()
    )


class ProductImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_id: UUID

    url: str
    alt_text: str | None

    sort_order: int
    is_primary: bool

# ---------Storefront product schemas--------------------------------------------


class ProductImageStorefrontRead(BaseModel):
    id: UUID
    url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool


class ProductStorefrontRead(BaseModel):
    id: UUID
    category_id: UUID
    name: str
    slug: str
    short_description: str | None
    description: str | None
    brand: str | None
    is_featured: bool

    seo_title: str | None
    seo_description: str | None

    images: list[ProductImageStorefrontRead] = []