from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.money import ZERO, money
from app.core.pagination import PageParams
from app.coupons.constants import DiscountType
from app.coupons.models import Coupon, CouponUsage
from app.coupons.repository import CouponRepository, CouponUsageRepository
from app.coupons.schemas import CouponCreate, CouponUpdate
from app.pricing.constants import PERCENT

logger = get_logger("coupons")

COUPON_NOT_FOUND = "Coupon not found"
SAVE_FAILED = "Unable to save coupon, please try again"
PERCENTAGE_TOO_LARGE = "Percentage discount value cannot exceed 100."
DATES_INVERTED = "Start date cannot be after expiration date."
USAGE_LIMIT_REACHED = "This coupon has reached its usage limit"


def _check_rules(
    discount_type: DiscountType | str,
    discount_value: Decimal | None,
    starts_at: datetime | None,
    expires_at: datetime | None,
) -> None:
    """Rules a coupon must satisfy however it arrived -- a 400, not a 422."""
    if (
        discount_type == DiscountType.PERCENTAGE
        and discount_value is not None
        and discount_value > PERCENT
    ):
        raise ValidationError(PERCENTAGE_TOO_LARGE)

    if starts_at is not None and expires_at is not None and starts_at >= expires_at:
        raise ValidationError(DATES_INVERTED)



class CouponService:
    """Manage coupon creation, lookup, validation, and redemption."""

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

    async def list(
        self,
        params: PageParams,
        *,
        active_only: bool = False,
    ) -> tuple[list[Coupon], int]:
        stmt = self.coupons.list_select(active_only=active_only)
        rows, total = await self.coupons.paginate(stmt, params)
        return list(rows), total

    async def create(self, data: CouponCreate) -> Coupon:
        _check_rules(
            data.discount_type, data.discount_value, data.starts_at, data.expires_at
        )

        code_upper = data.code.upper()
        existing = await self.coupons.get_by_code(code_upper)
        if existing is not None:
            raise ConflictError("A coupon with this code already exists")

        
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

        logger.info(
            "coupons.created tenant_id=%s code=%s",
            self.tenant_id,
            code_upper,
        )
        return coupon

    async def update(self, coupon_id: UUID, data: CouponUpdate) -> Coupon:
        coupon = await self.get(coupon_id)
        changes = data.model_dump(exclude_unset=True)

        _check_rules(
            changes.get("discount_type", coupon.discount_type),
            changes.get("discount_value", coupon.discount_value),
            changes.get("starts_at", coupon.starts_at),
            changes.get("expires_at", coupon.expires_at),
        )

        for field, value in changes.items():
            setattr(
                coupon, field, value.value if isinstance(value, DiscountType) else value
            )

        
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(SAVE_FAILED) from exc

        logger.info(
            "coupons.updated tenant_id=%s id=%s",
            self.tenant_id,
            coupon.id,
        )
        return coupon

    async def delete(self, coupon_id: UUID) -> None:
        """Deactivate the coupon without removing its usage history."""
        coupon = await self.get(coupon_id)
        coupon.is_active = False
        await self.session.commit()
        logger.info(
            "coupons.deactivated tenant_id=%s id=%s",
            self.tenant_id,
            coupon_id,
        )

    async def validated_discount(
        self,
        coupon: Coupon | None,
        subtotal: Decimal,
        customer_id: UUID,
    ) -> Decimal:
        """Validate a coupon and calculate the discount."""
        if coupon is None or not coupon.is_active:
            raise NotFoundError("Invalid or inactive coupon code")

        now = datetime.now(timezone.utc)
        if coupon.starts_at and now < coupon.starts_at:
            raise ValidationError("This coupon is not active yet")
        if coupon.expires_at and now > coupon.expires_at:
            raise ValidationError("This coupon has expired")

        # NULL means unlimited; 0 is a real "block everything" setting.
        if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
            raise ValidationError(USAGE_LIMIT_REACHED)

        if coupon.per_customer_usage_limit is not None:
            customer_uses = await self.usages.count_for_customer(
                coupon.id,
                customer_id,
            )
            if customer_uses >= coupon.per_customer_usage_limit:
                raise ValidationError(
                    "You have already reached the usage limit for this coupon"
                )

        if coupon.min_order_amount is not None and subtotal < coupon.min_order_amount:
            raise ValidationError(
                f"Minimum order amount of {coupon.min_order_amount} required for this coupon"
            )

        if coupon.discount_type == DiscountType.PERCENTAGE.value:
            raw_discount = subtotal * coupon.discount_value / PERCENT
            if (
                coupon.max_discount_amount is not None
                and raw_discount > coupon.max_discount_amount
            ):
                raw_discount = coupon.max_discount_amount
            discount = money(raw_discount)
        else:
            discount = money(coupon.discount_value)

        # Never negative, never more than what's actually being bought.
        discount = max(ZERO, min(discount, subtotal))

        return discount

    async def validate_and_calculate(
        self,
        code: str,
        subtotal: Decimal,
        customer_id: UUID,
    ) -> tuple[Coupon, Decimal]:
        """Validate a coupon and calculate its discount without consuming it."""
        coupon = await self.coupons.get_by_code(code)
        discount = await self.validated_discount(coupon, subtotal, customer_id)
        return coupon, discount

    async def lock_and_validate(
        self,
        code: str,
        subtotal: Decimal,
        customer_id: UUID,
    ) -> tuple[Coupon, Decimal]:
        """Lock, validate, and calculate a coupon discount."""
        coupon = await self.coupons.get_by_code_for_update(code)
        discount = await self.validated_discount(coupon, subtotal, customer_id)
        return coupon, discount

    async def redeem_for_order(
        self,
        code: str,
        subtotal: Decimal,
        customer_id: UUID,
        order_id: UUID,
    ) -> tuple[Coupon, Decimal]:
        """Lock, validate, and record a coupon redemption."""
        coupon, discount = await self.lock_and_validate(
            code,
            subtotal,
            customer_id,
        )
        await self.record_redemption(
            coupon,
            customer_id,
            order_id,
            discount,
        )
        return coupon, discount

    async def record_redemption(
        self,
        coupon: Coupon,
        customer_id: UUID,
        order_id: UUID,
        discount_amount: Decimal,
    ) -> CouponUsage:
        """Record a coupon redemption without committing the transaction."""
        coupon.times_used += 1
        usage = CouponUsage(
            coupon_id=coupon.id,
            customer_id=customer_id,
            order_id=order_id,
            discount_amount=discount_amount,
            used_at=datetime.now(timezone.utc),
        )
        return await self.usages.add(usage)

    async def record_usage(
        self,
        coupon_id: UUID,
        customer_id: UUID,
        order_id: UUID,
        discount_amount: Decimal,
    ) -> CouponUsage:
        """Record a coupon redemption and commit the transaction."""
        coupon = await self.get(coupon_id)
        usage = await self.record_redemption(
            coupon,
            customer_id,
            order_id,
            discount_amount,
        )
        await self.session.commit()
        logger.info(
            "coupons.used coupon_id=%s customer_id=%s order_id=%s",
            coupon_id,
            customer_id,
            order_id,
        )
        return usage