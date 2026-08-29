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
    MAX_OPTION_NAME_LENGTH,
    MAX_OPTION_VALUE_LENGTH,
    MAX_OPTIONS_PER_PRODUCT,
    MAX_SEO_DESCRIPTION_LENGTH,
    MAX_SEO_TITLE_LENGTH,
    MAX_SHORT_DESCRIPTION_LENGTH,
    MAX_SKU_LENGTH,
    MIN_PRODUCT_IMAGES,
    PRICE_PRECISION,
    PRICE_SCALE,
    CatalogueStatus,
    InventoryReason,
)

SKU_PATTERN = r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$"

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


# ----------------------------- CATEGORIES -----------------------------------


class CategoryCreate(BaseModel):
    name: str = Name
    description: str | None = Description
    status: CatalogueStatus = CatalogueStatus.ACTIVE

    _strip_name = field_validator("name")(_reject_blank)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    description: str | None = Description
    status: CatalogueStatus | None = None

    _strip_name = field_validator("name")(_reject_blank_optional)


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    status: CatalogueStatus


class CategoryStorefrontRead(BaseModel):
    """Public view. Omits tenant_id and lifecycle state."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None


# ------------------------------- IMAGES -------------------------------------


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


class ImageOrderItem(BaseModel):
    id: UUID
    sort_order: int = Field(ge=0)


class ImageReorderPayload(BaseModel):
    images: list[ImageOrderItem] = Field(min_length=1)


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
    """Public view. Exposes the URL only -- never a storage path or credential."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool


# ------------------------------- OPTIONS ------------------------------------


class VariantOptionValue(BaseModel):
    """One dimension of a variant, e.g. name="Color", value="Black"."""

    name: str = Field(min_length=1, max_length=MAX_OPTION_NAME_LENGTH)
    value: str = Field(min_length=1, max_length=MAX_OPTION_VALUE_LENGTH)

    _strip_name = field_validator("name")(_reject_blank)
    _strip_value = field_validator("value")(_reject_blank)


class ProductOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    position: int


class StorefrontOption(BaseModel):
    """An option plus every value that an in-stock variant actually offers."""

    name: str
    values: list[str]


# ------------------------------ INVENTORY -----------------------------------


class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    variant_id: UUID
    available_quantity: int
    reserved_quantity: int
    low_stock_threshold: int


class InventoryStatus(InventoryRead):
    sellable_quantity: int
    is_low_stock: bool


class InventorySet(BaseModel):
    available_quantity: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=255)


class InventoryAdjust(BaseModel):
    delta: int = Field(description="Signed change; negative removes stock")
    reason: InventoryReason = InventoryReason.ADJUSTMENT
    reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=255)

    @field_validator("delta")
    @classmethod
    def _reject_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("delta must not be zero")
        return value


class InventoryThreshold(BaseModel):
    low_stock_threshold: int = Field(ge=0)


class InventoryMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variant_id: UUID
    delta: int
    reason: InventoryReason
    reference: str | None
    note: str | None


# ------------------------------- VARIANTS -----------------------------------


class VariantCreate(BaseModel):
    sku: str = Sku
    name: str = Name
    price: Decimal = Price
    status: CatalogueStatus = CatalogueStatus.DRAFT

    options: list[VariantOptionValue] = Field(
        default_factory=list, max_length=MAX_OPTIONS_PER_PRODUCT
    )
    initial_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=0, ge=0)

    _strip_name = field_validator("name")(_reject_blank)

    @field_validator("options")
    @classmethod
    def _reject_duplicate_options(
        cls, value: list[VariantOptionValue]
    ) -> list[VariantOptionValue]:
        names = [option.name.lower() for option in value]
        if len(names) != len(set(names)):
            raise ValueError("an option name may only appear once per variant")
        return value


class VariantUpdate(BaseModel):
    sku: str | None = Field(
        default=None, min_length=1, max_length=MAX_SKU_LENGTH, pattern=SKU_PATTERN
    )
    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=PRICE_PRECISION, decimal_places=PRICE_SCALE
    )
    status: CatalogueStatus | None = None
    options: list[VariantOptionValue] | None = Field(
        default=None, max_length=MAX_OPTIONS_PER_PRODUCT
    )

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

    options: dict[str, str] = {}
    inventory: InventoryStatus | None = None


class VariantStorefrontRead(BaseModel):
    """Public view. Exposes availability, never raw reservation bookkeeping."""

    id: UUID
    product_id: UUID
    sku: str
    name: str
    price: Decimal
    options: dict[str, str] = {}
    in_stock: bool
    available_quantity: int


# ------------------------------- PRODUCTS -----------------------------------


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
    options: list[ProductOptionRead] = []


class ProductSummaryStorefrontRead(BaseModel):
    """
    Lightweight listing row.

    Carries only what a grid renders -- primary image and price range -- rather
    than every variant and image of every product.
    """

    id: UUID
    category_id: UUID
    name: str
    short_description: str | None
    brand: str | None
    is_featured: bool

    primary_image: ProductImageStorefrontRead | None = None
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    in_stock: bool = False


class ProductStorefrontRead(BaseModel):
    """Full public product. Omits tenant_id, lifecycle state and audit fields."""

    id: UUID
    category: CategoryStorefrontRead
    name: str
    short_description: str | None
    description: str | None
    brand: str | None
    is_featured: bool

    seo_title: str | None
    seo_description: str | None

    images: list[ProductImageStorefrontRead] = []
    options: list[StorefrontOption] = []
    variants: list[VariantStorefrontRead] = []

    price_from: Decimal | None = None
    price_to: Decimal | None = None
    in_stock: bool = False
