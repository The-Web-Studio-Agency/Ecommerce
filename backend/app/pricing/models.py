"""
What the store adds on top of the goods.

Two settings rows per tenant -- one flat shipping charge, one tax percentage --
and nothing else. No zones, no jurisdictions, no rules: whatever a tenant puts
here is what every order of theirs is charged.
"""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.catalogue.constants import PRICE_PRECISION, PRICE_SCALE
from app.models.base import Base, TimestampMixin
from app.pricing.constants import MAX_TAX_PERCENTAGE

# 999.99 is plenty for a percentage; the check constraint holds it to 100.
TAX_PRECISION = 5
TAX_SCALE = 2


class ShippingSettings(Base, TimestampMixin):
    """
    One tenant's delivery charge.

    `free_shipping_minimum` is optional. Left NULL, every order pays
    `shipping_amount`; set, an order at or above it ships free.
    """

    __tablename__ = "shipping_settings"

    __table_args__ = (
        # One configuration per tenant, enforced here rather than in Python so
        # two concurrent first-writes cannot create a second row.
        UniqueConstraint("tenant_id", name="uq_shipping_settings_tenant_id"),
        CheckConstraint("shipping_amount >= 0", name="shipping_amount_not_negative"),
        CheckConstraint(
            "free_shipping_minimum IS NULL OR free_shipping_minimum >= 0",
            name="free_shipping_minimum_not_negative",
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

    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )

    free_shipping_minimum: Mapped[Decimal | None] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True
    )

    # Switched off means the tenant charges nothing for delivery, which is also
    # what a tenant with no row at all gets.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TaxSettings(Base, TimestampMixin):
    """One tenant's tax rate, as a percentage: 18.00 means 18%."""

    __tablename__ = "tax_settings"

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tax_settings_tenant_id"),
        CheckConstraint(
            f"tax_percentage >= 0 AND tax_percentage <= {MAX_TAX_PERCENTAGE}",
            name="tax_percentage_in_range",
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

    tax_percentage: Mapped[Decimal] = mapped_column(
        Numeric(TAX_PRECISION, TAX_SCALE), nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
