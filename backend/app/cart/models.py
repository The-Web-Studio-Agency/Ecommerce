import uuid
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CartStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONVERTED = "CONVERTED"


_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in CartStatus)


class Cart(Base, TimestampMixin):
    """A customer's working basket. One ACTIVE cart per customer per tenant."""

    __tablename__ = "carts"

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_carts_tenant_id_id"),
        # Composite foreign key: a cart cannot point at a user in another
        # tenant, which is the same pattern the catalogue tables use.
        ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["users.tenant_id", "users.id"],
            name="fk_carts_tenant_customer_users",
            ondelete="CASCADE",
        ),
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="status_valid"),
        # "One active cart" is enforced here rather than in Python, so two
        # concurrent first-requests cannot each create one.
        Index(
            "uq_carts_one_active_per_customer",
            "tenant_id",
            "customer_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CartStatus.ACTIVE.value
    )


class CartItem(Base, TimestampMixin):
    """
    A variant and how many of it the customer wants.

    Deliberately stores no product name, SKU, price or image: those are read
    from the catalogue when the cart is rendered, so a price or name change is
    reflected immediately instead of going stale in the basket.
    """

    __tablename__ = "cart_items"

    __table_args__ = (
        # One row per variant per cart -- adding the same variant again bumps
        # the quantity rather than creating a second line.
        UniqueConstraint("cart_id", "variant_id", name="uq_cart_items_cart_variant"),
        ForeignKeyConstraint(
            ["tenant_id", "cart_id"],
            ["carts.tenant_id", "carts.id"],
            name="fk_cart_items_tenant_cart_carts",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "variant_id"],
            ["product_variants.tenant_id", "product_variants.id"],
            name="fk_cart_items_tenant_variant_product_variants",
            ondelete="CASCADE",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("ix_cart_items_tenant_id_cart_id", "tenant_id", "cart_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    cart_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
