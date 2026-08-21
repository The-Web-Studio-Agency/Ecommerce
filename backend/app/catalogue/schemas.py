from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.catalogue.constants import (
    MAX_ALT_TEXT_LENGTH,
    MAX_BRAND_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_IMAGE_URL_LENGTH,
    MAX_NAME_LENGTH,
    MAX_SEO_DESCRIPTION_LENGTH,
    MAX_SEO_TITLE_LENGTH,
    MAX_SHORT_DESCRIPTION_LENGTH,
    MAX_SKU_LENGTH,
    PRICE_PRECISION,
    PRICE_SCALE,
    CatalogueStatus,
)

SKU_PATTERN = r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$"

MIN_PRODUCT_IMAGES = 1

Name = Field(min_length=1, max_length=MAX_NAME_LENGTH)
Sku = Field(min_length=1, max_length=MAX_SKU_LENGTH, pattern=SKU_PATTERN)
Description = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
Price = Field(ge=0, max_digits=PRICE_PRECISION, decimal_places=PRICE_SCALE)


def _reject_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value.strip()


def _reject_blank_optional(value: str | None) -> str | None:
    return value if value is None else _reject_blank(value)


def _strip_optional(value: str | None) -> str | None:
    return value if value is None else value.strip()


# ----Category Schemas--------------------------------------------

class CategoryCreate(BaseModel):
    name: str = Name
    description: str | None = Description
    is_active: bool = True

    _strip_name = field_validator("name")(_reject_blank)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    description: str | None = Description
    is_active: bool | None = None

    _strip_name = field_validator("name")(_reject_blank_optional)


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    is_active: bool


class CategoryStorefrontRead(BaseModel):
    """Public view of a category. Deliberately omits tenant_id."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None


# -----------------------PRODUCT IMAGE SCHEMAS--------------------------------------------

class ProductImageCreate(BaseModel):
    url: str = Field(min_length=1, max_length=MAX_IMAGE_URL_LENGTH)
    alt_text: str | None = Field(default=None, max_length=MAX_ALT_TEXT_LENGTH)
    sort_order: int = Field(default=0, ge=0)
    is_primary: bool = False

    _strip_url = field_validator("url")(_reject_blank)
    _strip_alt_text = field_validator("alt_text")(_strip_optional)


class ProductImageUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=1, max_length=MAX_IMAGE_URL_LENGTH)
    alt_text: str | None = Field(default=None, max_length=MAX_ALT_TEXT_LENGTH)
    sort_order: int | None = Field(default=None, ge=0)
    is_primary: bool | None = None

    _strip_url = field_validator("url")(_reject_blank_optional)
    _strip_alt_text = field_validator("alt_text")(_strip_optional)


class ProductImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_id: UUID

    url: str
    alt_text: str | None

    sort_order: int
    is_primary: bool


class ProductImageStorefrontRead(BaseModel):
    """Public view of a product image. Deliberately omits tenant_id."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool


# -------------------------PRODUCT SCHEMAS--------------------------------------------


class ProductCreate(BaseModel):
    category_id: UUID
    name: str = Name
    short_description: str | None = Field(
        default=None, max_length=MAX_SHORT_DESCRIPTION_LENGTH
    )
    description: str | None = Description
    brand: str | None = Field(default=None, max_length=MAX_BRAND_LENGTH)
    status: CatalogueStatus = CatalogueStatus.DRAFT
    is_featured: bool = False
    seo_title: str | None = Field(default=None, max_length=MAX_SEO_TITLE_LENGTH)
    seo_description: str | None = Field(
        default=None, max_length=MAX_SEO_DESCRIPTION_LENGTH
    )

    # A product is never listable without artwork, so at least one image is
    # required up front rather than left to a follow-up call.
    images: list[ProductImageCreate] = Field(min_length=MIN_PRODUCT_IMAGES)

    _strip_name = field_validator("name")(_reject_blank)
    _strip_short_description = field_validator("short_description")(_strip_optional)
    _strip_brand = field_validator("brand")(_strip_optional)

    @field_validator("images")
    @classmethod
    def _at_most_one_primary(
        cls, value: list[ProductImageCreate]
    ) -> list[ProductImageCreate]:
        if sum(1 for image in value if image.is_primary) > 1:
            raise ValueError("only one image can be marked as primary")
        return value


class ProductUpdate(BaseModel):
    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    short_description: str | None = Field(
        default=None, max_length=MAX_SHORT_DESCRIPTION_LENGTH
    )
    description: str | None = Description
    brand: str | None = Field(default=None, max_length=MAX_BRAND_LENGTH)
    status: CatalogueStatus | None = None
    is_featured: bool | None = None
    seo_title: str | None = Field(default=None, max_length=MAX_SEO_TITLE_LENGTH)
    seo_description: str | None = Field(
        default=None, max_length=MAX_SEO_DESCRIPTION_LENGTH
    )

    _strip_name = field_validator("name")(_reject_blank_optional)
    _strip_short_description = field_validator("short_description")(_strip_optional)
    _strip_brand = field_validator("brand")(_strip_optional)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    category_id: UUID
    name: str
    short_description: str | None
    description: str | None
    brand: str | None
    status: CatalogueStatus
    is_featured: bool
    seo_title: str | None
    seo_description: str | None

    images: list[ProductImageRead] = []


class ProductStorefrontRead(BaseModel):
    """Public view of a product. Deliberately omits tenant_id and status."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    name: str
    short_description: str | None
    description: str | None
    brand: str | None
    is_featured: bool

    seo_title: str | None
    seo_description: str | None

    images: list[ProductImageStorefrontRead] = []


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
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=PRICE_PRECISION, decimal_places=PRICE_SCALE
    )
    status: CatalogueStatus | None = None

    _strip_name = field_validator("name")(_reject_blank_optional)


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_id: UUID
    sku: str
    name: str
    price: Decimal
    status: CatalogueStatus


class VariantStorefrontRead(BaseModel):
    """Public view of a variant. Deliberately omits tenant_id."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    sku: str
    name: str
    price: Decimal
