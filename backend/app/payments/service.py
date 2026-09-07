from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.pagination import PageParams
from app.orders.repository import OrderRepository
from app.payments.constants import PaymentStatus
from app.payments.models import Payment
from app.payments.repository import PaymentRepository

PAYMENT_NOT_FOUND = "Payment not found"


class PaymentService:
    """Read-only access to payments, scoped to one tenant."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.payments = PaymentRepository(session, tenant_id)
        self.orders = OrderRepository(session, tenant_id)

    async def get(self, payment_id: UUID) -> Payment:
        """Admin lookup: any payment in this tenant."""
        payment = await self.payments.get(payment_id)
        if payment is None:
            raise NotFoundError(PAYMENT_NOT_FOUND)
        return payment

    async def get_for_customer(self, customer_id: UUID, payment_id: UUID) -> Payment:
        """Fetch a payment on one of the customer's own orders."""
        payment = await self.get(payment_id)

        order = await self.orders.get_for_customer(customer_id, payment.order_id)
        if order is None:
            raise NotFoundError(PAYMENT_NOT_FOUND)

        return payment

    async def list(
        self,
        params: PageParams,
        *,
        order_id: UUID | None = None,
        status: PaymentStatus | None = None,
    ) -> tuple[list[Payment], int]:
        stmt = self.payments.list_select(order_id=order_id, status=status)
        rows, total = await self.payments.paginate(stmt, params)
        return list(rows), total
