from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from app.catalogue.constants import PRICE_PRECISION, PRICE_SCALE
from app.pricing.constants import MAX_TAX_PERCENTAGE

MAX_MONEY = Decimal(10) ** (PRICE_PRECISION - PRICE_SCALE) - Decimal("0.01")


class ShippingSettingsUpdate(BaseModel):
    shipping_amount: Decimal = Field(ge=0, le=MAX_MONEY, decimal_places=PRICE_SCALE)
    free_shipping_minimum: Decimal | None = Field(
        default=None, ge=0, le=MAX_MONEY, decimal_places=PRICE_SCALE
    )
    is_active: bool = True


class ShippingSettingsRead(BaseModel):
    shipping_amount: Decimal
    free_shipping_minimum: Decimal | None
    is_active: bool


class TaxSettingsUpdate(BaseModel):
    tax_percentage: Decimal = Field(ge=0, le=MAX_TAX_PERCENTAGE, decimal_places=2)
    is_active: bool = True


class TaxSettingsRead(BaseModel):
    tax_percentage: Decimal
    is_active: bool
