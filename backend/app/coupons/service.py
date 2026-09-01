from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.money import money
from app.core.pagination import PageParams
from app.coupons.constants import DiscountType
from app.coupons.models import Coupon, CouponUsage
from app.coupons.repository import CouponRepository, CouponUsageRepository
from app.coupons.schemas import CouponCreate, CouponUpdate

logger = get_logger("coupons")

COUPON_NOT_FOUND = "Coupon not found"
SAVE_FAILED = "Unable to save coupon, please try again"


class CouponService:
    """Manages creation, lookup, administration, validation, and redemption of discount coupons."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.coupons = CouponRepository(session, tenant_id)
        self.usages = CouponUsageRepository(session, tenant_id)

    async def get(self, coupon_id: UUID) -> Coupon:
        coupon = await self.coupons.get(coupon_id)
        if coupon is None:
            raise NotFoundError(COUPON_NOT_FOUND)
        return coupon

    async def list(self, params: PageParams, *, active_only: bool = False) -> tuple[list[Coupon], int]:
        stmt = self.coupons.list_select(active_only=active_only)
        rows, total = await self.coupons.paginate(stmt, params)
        return list(rows), total

    async def create(self, data: CouponCreate) -> Coupon:
        code_upper = data.code.upper()
        existing = await self.coupons.get_by_code(code_upper)
        if existing is not None:
            raise ConflictError("A coupon with this code already exists")

        if data.discount_type == DiscountType.PERCENTAGE and data.discount_value > 100:
            raise ValidationError("Percentage discount cannot exceed 100")

        if data.starts_at and data.expires_at and data.starts_at >= data.expires_at:
            raise ValidationError("Start date must be earlier than expiry date")

        try:
            coupon = Coupon(
                code=code_upper,
                discount_type=data.discount_type.value,
                discount_value=data.discount_value,
                min_order_amount=data.min_order_amount,
                max_discount_amount=data.max_discount_amount,
                starts_at=data.starts_at,
                expires_at=data.expires_at,
                usage_limit=data.usage_limit,
                per_customer_usage_limit=data.per_customer_usage_limit,
                is_active=data.is_active,
            )
            await self.coupons.add(coupon)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(SAVE_FAILED) from exc

        logger.info("coupons.created tenant_id=%s code=%s", self.tenant_id, code_upper)
        return coupon

    async def update(self, coupon_id: UUID, data: CouponUpdate) -> Coupon:
        coupon = await self.get(coupon_id)

        if data.discount_type is not None:
            coupon.discount_type = data.discount_type.value
        if data.discount_value is not None:
            coupon.discount_value = data.discount_value
        if data.min_order_amount is not None:
            coupon.min_order_amount = data.min_order_amount
        if data.max_discount_amount is not None:
            coupon.max_discount_amount = data.max_discount_amount
        if data.starts_at is not None:
            coupon.starts_at = data.starts_at
        if data.expires_at is not None:
            coupon.expires_at = data.expires_at
        if data.usage_limit is not None:
            coupon.usage_limit = data.usage_limit
        if data.per_customer_usage_limit is not None:
            coupon.per_customer_usage_limit = data.per_customer_usage_limit
        if data.is_active is not None:
            coupon.is_active = data.is_active

        if coupon.discount_type == DiscountType.PERCENTAGE.value and coupon.discount_value > 100:
            raise ValidationError("Percentage discount cannot exceed 100")

        if coupon.starts_at and coupon.expires_at and coupon.starts_at >= coupon.expires_at:
            raise ValidationError("Start date must be earlier than expiry date")

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(SAVE_FAILED) from exc

        logger.info("coupons.updated tenant_id=%s id=%s", self.tenant_id, coupon.id)
        return coupon

    async def delete(self, coupon_id: UUID) -> None:
        coupon = await self.get(coupon_id)
        await self.coupons.delete(coupon)
        await self.session.commit()
        logger.info("coupons.deleted tenant_id=%s id=%s", self.tenant_id, coupon_id)

    async def validate_and_calculate(self, code: str, subtotal: Decimal, customer_id: UUID) -> tuple[Coupon, Decimal]:
        """Validates a coupon code against subtotal and customer history, returning the computed discount."""
        coupon = await self.coupons.get_by_code(code)
        if coupon is None or not coupon.is_active:
            raise NotFoundError("Invalid or inactive coupon code")

        now = datetime.now(timezone.utc)
        if coupon.starts_at and now < coupon.starts_at:
            raise ValidationError("This coupon is not active yet")
        if coupon.expires_at and now > coupon.expires_at:
            raise ValidationError("This coupon has expired")

        if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
            raise ValidationError("This coupon has reached its usage limit")

        if coupon.per_customer_usage_limit is not None:
            customer_uses = await self.usages.count_for_customer(coupon.id, customer_id)
            if customer_uses >= coupon.per_customer_usage_limit:
                raise ValidationError("You have already reached the usage limit for this coupon")

        if coupon.min_order_amount is not None and subtotal < coupon.min_order_amount:
            raise ValidationError(f"Minimum order amount of {coupon.min_order_amount} required for this coupon")

        if coupon.discount_type == DiscountType.PERCENTAGE.value:
            raw_discount = subtotal * coupon.discount_value / Decimal(100)
            if coupon.max_discount_amount is not None and raw_discount > coupon.max_discount_amount:
                raw_discount = coupon.max_discount_amount
            discount = money(raw_discount)
        else:
            discount = money(coupon.discount_value)

        # Ensure discount does not exceed subtotal
        if discount > subtotal:
            discount = subtotal

        return coupon, discount

    async def record_usage(self, coupon_id: UUID, customer_id: UUID, order_id: UUID, discount_amount: Decimal) -> CouponUsage:
        """Records a coupon redemption and increments the global usage counter."""
        coupon = await self.get(coupon_id)
        coupon.times_used += 1

        usage = CouponUsage(
            tenant_id=self.tenant_id,
            coupon_id=coupon.id,
            customer_id=customer_id,
            order_id=order_id,
            discount_amount=discount_amount,
            used_at=datetime.now(timezone.utc),
        )
        await self.usages.add(usage)
        await self.session.commit()
        logger.info("coupons.used coupon_id=%s customer_id=%s order_id=%s", coupon_id, customer_id, order_id)
        return usage