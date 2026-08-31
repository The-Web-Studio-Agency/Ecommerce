from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.orders.constants import OrderStatus, PaymentStatus
from app.payments.schemas import PaymentRead


class CheckoutItem(BaseModel):
    """One validated line, priced from the database."""

    product_id: UUID
    variant_id: UUID
    product_name: str
    variant_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class CheckoutPreview(BaseModel):
    items: list[CheckoutItem]
    subtotal: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class CheckoutCreate(BaseModel):
    """The only thing checkout accepts from the client: which address to deliver to."""

    address_id: UUID


class DeliveryAddressRead(BaseModel):
    full_name: str
    phone: str
    address_line_1: str
    address_line_2: str | None
    city: str
    state: str
    postal_code: str
    country: str


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    variant_id: UUID
    product_name: str
    variant_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderRead(BaseModel):
    id: UUID
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    items: list[OrderItemRead]
    subtotal: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    payment: PaymentRead | None
    delivery_address: DeliveryAddressRead
    created_at: datetime


class OrderSummaryRead(BaseModel):
    """A row in a list of orders -- no items, so listing stays cheap to read."""

    id: UUID
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    total_amount: Decimal
    currency: str
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
