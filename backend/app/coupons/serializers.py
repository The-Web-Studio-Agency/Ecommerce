"""Turn coupon rows into API payloads."""

from __future__ import annotations

from app.coupons.models import Coupon
from app.coupons.schemas import CouponRead


def coupon_read(coupon: Coupon, currency: str) -> CouponRead:
    return CouponRead(
        id=coupon.id,
        code=coupon.code,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        currency=currency,
        min_order_amount=coupon.min_order_amount,
        max_discount_amount=coupon.max_discount_amount,
        starts_at=coupon.starts_at,
        expires_at=coupon.expires_at,
        usage_limit=coupon.usage_limit,
        per_customer_usage_limit=coupon.per_customer_usage_limit,
        times_used=coupon.times_used,
        is_active=coupon.is_active,
        created_at=coupon.created_at,
    )