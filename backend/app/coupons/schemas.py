from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.catalogue.constants import PRICE_PRECISION, PRICE_SCALE
from app.coupons.constants import DiscountType

MAX_MONEY = Decimal(10) ** (PRICE_PRECISION - PRICE_SCALE) - Decimal("0.01")


class CouponCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    discount_type: DiscountType
    discount_value: Decimal = Field(
        gt=0,
        le=MAX_MONEY, 
        decimal_places=PRICE_SCALE,
        )
    min_order_amount: Decimal | None = Field(
        default=None, 
        ge=0, 
        le=MAX_MONEY, 
        decimal_places=PRICE_SCALE,
        )
    max_discount_amount: Decimal | None = Field(
        default=None, 
        ge=0, 
        le=MAX_MONEY, 
        decimal_places=PRICE_SCALE,
        )
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=0)
    per_customer_usage_limit: int | None = Field(default=None, ge=0)
    is_active: bool = True


class CouponUpdate(BaseModel):
    discount_type: DiscountType | None = None
    discount_value: Decimal | None = Field(
        default=None, 
        gt=0, 
        le=MAX_MONEY, 
        decimal_places=PRICE_SCALE)
    min_order_amount: Decimal | None = Field(
        default=None, 
        ge=0, 
        le=MAX_MONEY, 
        decimal_places=PRICE_SCALE,
        )
    max_discount_amount: Decimal | None = Field(
        default=None, 
        ge=0, le=MAX_MONEY, 
        decimal_places=PRICE_SCALE,
        )
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=0)
    per_customer_usage_limit: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CouponRead(BaseModel):
    id: UUID
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    currency: str
    min_order_amount: Decimal | None
    max_discount_amount: Decimal | None
    starts_at: datetime | None
    expires_at: datetime | None
    usage_limit: int | None
    per_customer_usage_limit: int | None
    times_used: int
    is_active: bool
    created_at: datetime


class CouponApplyRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)


class CouponApplyResponse(BaseModel):
    code: str
    discount_amount: Decimal
    currency: str