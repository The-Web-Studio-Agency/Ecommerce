import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.catalogue.constants import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    MAX_SKU_LENGTH,
    MAX_SLUG_LENGTH,
    PRICE_PRECISION,
    PRICE_SCALE,
    CatalogueStatus,
)
from app.models.base import Base, TimestampMixin

_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in CatalogueStatus)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_categories_tenant_slug"),
        UniqueConstraint("tenant_id", "id", name="uq_categories_tenant_id_id"),
        CheckConstraint("slug = lower(slug)", name="slug_is_lowercase"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(MAX_NAME_LENGTH), nullable=False)

    slug: Mapped[str] = mapped_column(String(MAX_SLUG_LENGTH), nullable=False)

    description: Mapped[str | None] = mapped_column(
        String(MAX_DESCRIPTION_LENGTH), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "slug",
            name="uq_products_tenant_slug",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_products_tenant_id_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "category_id"],
            ["categories.tenant_id", "categories.id"],
            name="fk_products_tenant_category_categories",
            ondelete="NO ACTION",
        ),
        CheckConstraint(
            "slug = lower(slug)",
            name="slug_is_lowercase",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="name_not_blank",
        ),
        CheckConstraint(
            f"status IN ({_STATUS_VALUES})",
            name="status_valid",
        ),
        Index(
            "ix_products_tenant_id_category_id",
            "tenant_id",
            "category_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(MAX_NAME_LENGTH),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(MAX_SLUG_LENGTH),
        nullable=False,
    )

    short_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(MAX_DESCRIPTION_LENGTH),
        nullable=True,
    )

    brand: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CatalogueStatus.DRAFT.value,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    seo_title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    seo_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"

    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_product_variants_tenant_sku"),
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            name="fk_product_variants_tenant_product_products",
            ondelete="CASCADE",
        ),
        CheckConstraint("sku = upper(sku)", name="sku_is_uppercase"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="status_valid"),
        CheckConstraint("price >= 0", name="price_not_negative"),
        Index("ix_product_variants_tenant_id_product_id", "tenant_id", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    sku: Mapped[str] = mapped_column(String(MAX_SKU_LENGTH), nullable=False)

    name: Mapped[str] = mapped_column(String(MAX_NAME_LENGTH), nullable=False)

    price: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CatalogueStatus.DRAFT.value,
    )


class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_images"

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            name="fk_product_images_tenant_product_products",
            ondelete="CASCADE",
        ),
        Index(
            "ix_product_images_tenant_id_product_id",
            "tenant_id",
            "product_id",
        ),
        CheckConstraint(
            "length(trim(url)) > 0",
            name="image_url_not_blank",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="image_sort_order_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    alt_text: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    sort_order: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )