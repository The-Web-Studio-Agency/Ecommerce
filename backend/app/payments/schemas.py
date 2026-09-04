from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.core.pagination import PageParams
from app.payments.constants import PaymentProvider, PaymentStatus


class PaymentRead(BaseModel):
    """A payment as the API reports it."""

    id: UUID
    order_id: UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: PaymentProvider
    created_at: datetime


class PaymentQuery(PageParams):
    """Filters the admin payment listing accepts."""

    order_id: UUID | None = None
    status: PaymentStatus | None = None
