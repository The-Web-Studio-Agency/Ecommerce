from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import StrictModel

MAX_ITEM_QUANTITY = 999


class CartItemCreate(StrictModel):
    variant_id: UUID
    quantity: int = Field(default=1, ge=1, le=MAX_ITEM_QUANTITY)


class CartItemUpdate(StrictModel):
    quantity: int = Field(ge=1, le=MAX_ITEM_QUANTITY)


class CartItemImage(BaseModel):
    url: str
    alt_text: str | None = None


class CartItemRead(BaseModel):
    id: UUID
    variant_id: UUID
    product_id: UUID
    product_name: str
    variant_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    image: CartItemImage | None = None


class CartRead(BaseModel):
    id: UUID
    items: list[CartItemRead] = []
    subtotal: Decimal = Decimal("0.00")
    item_count: int = 0
