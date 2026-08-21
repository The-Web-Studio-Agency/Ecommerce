from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

MAX_ITEM_QUANTITY = 999


class CartItemCreate(BaseModel):
    variant_id: UUID
    quantity: int = Field(default=1, ge=1, le=MAX_ITEM_QUANTITY)


class CartItemUpdate(BaseModel):
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
    # Prices are read from the database and sent as Decimal -- never floats,
    # and never taken from the request.
    unit_price: Decimal
    subtotal: Decimal
    image: CartItemImage | None = None


class CartRead(BaseModel):
    id: UUID
    items: list[CartItemRead] = []
    subtotal: Decimal = Decimal("0.00")
    item_count: int = 0
