from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.catalogue.constants import PRICE_SCALE
from app.core.money import MAX_MONEY
from app.coupons.constants import DiscountType


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

    @model_validator(mode="after")
    def validate_coupon(self):
        if(
            self.discount_type == DiscountType.PERCENTAGE and self.discount_value > 100
        ):
            raise ValueError("Percentage discount value cannot exceed 100.")
        if(
            self.starts_at is not None 
            and self.expires_at is not None 
            and self.starts_at >= self.expires_at
        ):
            raise ValueError("Start date cannot be after expiration date.")
        return self

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

    @model_validator(mode="after")
    def validate_coupon(self):
        if(
            self.discount_type == DiscountType.PERCENTAGE and self.discount_value > 100
        ):
            raise ValueError("Percentage discount value cannot exceed 100.")
        if(
            self.starts_at is not None 
            and self.expires_at is not None 
            and self.starts_at >= self.expires_at
        ):
            raise ValueError("Start date cannot be after expiration date.")
        return self

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