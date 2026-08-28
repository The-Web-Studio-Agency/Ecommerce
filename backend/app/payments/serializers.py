"""Turn payment rows into API payloads."""

from __future__ import annotations

from app.payments.models import Payment
from app.payments.schemas import PaymentRead


def payment_read(payment: Payment, currency: str) -> PaymentRead:
    """
    `currency` comes from the tenant, not from the payment.

    A storefront prices in one currency, so it is carried on the tenant rather
    than copied onto every row -- and passed in here so a payment can never be
    rendered with somebody else's.
    """
    return PaymentRead(
        id=payment.id,
        order_id=payment.order_id,
        amount=payment.amount,
        currency=currency,
        status=payment.status,
        provider=payment.provider,
        created_at=payment.created_at,
    )
