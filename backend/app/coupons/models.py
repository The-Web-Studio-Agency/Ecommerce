from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.catalogue.constants import PRICE_PRECISION, PRICE_SCALE
from app.coupons.constants import DiscountType
from app.models.base import Base, TimestampMixin

_DISCOUNT_TYPE_VALUES = ", ".join(f"'{t.value}'" for t in DiscountType)


class Coupon(Base, TimestampMixin):
    """Discount vouchers usable during checkout."""

    __tablename__ = "coupons"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_coupons_tenant_id_code"),
        CheckConstraint(f"discount_type IN ({_DISCOUNT_TYPE_VALUES})", name="discount_type_valid"),
        CheckConstraint("discount_value > 0", name="discount_value_positive"),
        CheckConstraint(
            "discount_type != 'PERCENTAGE' OR discount_value <= 100",
            name="percentage_max_100",
        ),
        CheckConstraint(
            "min_order_amount IS NULL OR min_order_amount >= 0",
            name="min_order_amount_not_negative",
        ),
        CheckConstraint(
            "max_discount_amount IS NULL OR max_discount_amount >= 0",
            name="max_discount_amount_not_negative",
        ),
        CheckConstraint(
            "usage_limit IS NULL OR usage_limit >= 0",
            name="usage_limit_not_negative",
        ),
        CheckConstraint(
            "per_customer_usage_limit IS NULL OR per_customer_usage_limit >= 0",
            name="per_customer_usage_limit_not_negative",
        ),
        CheckConstraint("times_used >= 0", name="times_used_not_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False)

    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)

    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )

    min_order_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True
    )

    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True
    )

    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    per_customer_usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CouponUsage(Base, TimestampMixin):
    """Tracks historical coupon redemption per order and customer."""

    __tablename__ = "coupon_usages"

    __table_args__ = (
        UniqueConstraint("tenant_id", "order_id", name="uq_coupon_usages_tenant_id_order_id"),
        CheckConstraint("discount_amount >= 0", name="discount_amount_not_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coupons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )

    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)