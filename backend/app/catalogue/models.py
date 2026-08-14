"""Catalogue tables: Category -> Product -> ProductVariant.

Tenant ownership is enforced by the DATABASE, not only by the repository layer.
Each child table carries `tenant_id` and references its parent through a
COMPOSITE foreign key on `(tenant_id, parent_id)`. That is what makes a
cross-tenant reference - a product in tenant A pointing at a category in tenant
B - impossible to store at all, rather than merely unlikely because the service
remembered to check. It is the reason each table also carries a
`UNIQUE (tenant_id, id)`: a composite foreign key needs one to point at.

Neither Product nor ProductVariant holds a stock quantity. Inventory is a
separate module and will own that, per variant.
"""

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
        # One slug per tenant. Two tenants may both have "t-shirts".
        UniqueConstraint("tenant_id", "slug", name="uq_categories_tenant_slug"),
        # Target for the composite foreign key on products. Redundant as a
        # uniqueness rule (id is already the primary key); it exists so the
        # database can verify a product's category belongs to its tenant.
        UniqueConstraint("tenant_id", "id", name="uq_categories_tenant_id_id"),
        # Slugs are lowercased by the service. Enforcing it here is what makes
        # the uniqueness constraint above actually case-insensitive, exactly as
        # ck_users_email_is_lowercase does for users.
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
        # No explicit index: tenant_id leads uq_categories_tenant_slug, which
        # every tenant-scoped read can already use.
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
        UniqueConstraint("tenant_id", "slug", name="uq_products_tenant_slug"),
        UniqueConstraint("tenant_id", "id", name="uq_products_tenant_id_id"),
        # The category must belong to the SAME tenant as the product. A plain
        # foreign key on category_id alone would happily accept another
        # tenant's category id.
        ForeignKeyConstraint(
            ["tenant_id", "category_id"],
            ["categories.tenant_id", "categories.id"],
            name="fk_products_tenant_category_categories",
            # NO ACTION, not RESTRICT: both refuse to delete a category that
            # still has products, but RESTRICT is checked immediately while NO
            # ACTION is checked at the end of the statement. Deleting a tenant
            # cascades to categories AND products in one statement, and under
            # RESTRICT that fails depending on which cascade Postgres runs
            # first. The service reports the in-use case as a 409 before the
            # database ever sees it.
            ondelete="NO ACTION",
        ),
        CheckConstraint("slug = lower(slug)", name="slug_is_lowercase"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="status_valid"),
        # Listing a category's products, and the RESTRICT check above.
        Index("ix_products_tenant_id_category_id", "tenant_id", "category_id"),
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

    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    name: Mapped[str] = mapped_column(String(MAX_NAME_LENGTH), nullable=False)

    slug: Mapped[str] = mapped_column(String(MAX_SLUG_LENGTH), nullable=False)

    description: Mapped[str | None] = mapped_column(
        String(MAX_DESCRIPTION_LENGTH), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CatalogueStatus.DRAFT.value,
    )


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"

    __table_args__ = (
        # A SKU identifies one sellable item within a tenant's catalogue, so it
        # is unique per tenant rather than per product.
        UniqueConstraint("tenant_id", "sku", name="uq_product_variants_tenant_sku"),
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            name="fk_product_variants_tenant_product_products",
            # A variant is part of its product, not a reference to it: deleting
            # the product takes its variants with it.
            ondelete="CASCADE",
        ),
        CheckConstraint("sku = upper(sku)", name="sku_is_uppercase"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="status_valid"),
        # Money is never negative. Free is representable; owing the customer is
        # not a price.
        CheckConstraint("price >= 0", name="price_not_negative"),
        # Listing one product's variants is the module's hottest read.
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

    #: How this variant differs from its siblings, e.g. "Small / Black".
    #: Deliberately one label rather than a dynamic attribute engine.
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
