from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.payments.constants import PaymentProvider, PaymentStatus


class PaymentRead(BaseModel):
    """
    A payment as the API reports it.

    No customer id -- a caller who can read this already had to prove which
    order is theirs.
    """

    id: UUID
    order_id: UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: PaymentProvider
    created_at: datetime
