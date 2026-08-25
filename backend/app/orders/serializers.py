"""Turn order rows into API payloads."""

from __future__ import annotations

from app.orders.models import Order
from app.orders.schemas import DeliveryAddressRead, OrderItemRead, OrderRead


def delivery_address(order: Order) -> DeliveryAddressRead:
    return DeliveryAddressRead(
        full_name=order.delivery_name,
        phone=order.delivery_phone,
        address_line_1=order.delivery_address_line_1,
        address_line_2=order.delivery_address_line_2,
        city=order.delivery_city,
        state=order.delivery_state,
        postal_code=order.delivery_postal_code,
        country=order.delivery_country,
    )


def order_read(order: Order) -> OrderRead:
    return OrderRead(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_status=order.payment_status,
        items=[OrderItemRead.model_validate(item) for item in order.items],
        subtotal=order.subtotal,
        shipping_amount=order.shipping_amount,
        total_amount=order.total_amount,
        delivery_address=delivery_address(order),
        created_at=order.created_at,
    )
