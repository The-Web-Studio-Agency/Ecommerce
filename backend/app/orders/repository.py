from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select

from app.core.repository import TenantScopedRepository
from app.orders.constants import OrderStatus, PaymentStatus
from app.orders.models import Order, OrderItem


def _escape_like(term: str) -> str:
    """Neutralise LIKE wildcards so a search term cannot widen its own match."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class OrderRepository(TenantScopedRepository[Order]):
    model = Order

    def list_select(
        self,
        *,
        customer_id: UUID | None = None,
        order_number: str | None = None,
        status: OrderStatus | None = None,
        payment_status: PaymentStatus | None = None,
    ) -> Select[tuple[Order]]:
        stmt = self.base_select()

        if customer_id is not None:
            stmt = stmt.where(Order.customer_id == customer_id)

        if order_number:
            pattern = f"%{_escape_like(order_number.strip())}%"
            stmt = stmt.where(Order.order_number.ilike(pattern, escape="\\"))

        if status is not None:
            stmt = stmt.where(Order.status == status.value)

        if payment_status is not None:
            stmt = stmt.where(Order.payment_status == payment_status.value)

        return stmt.order_by(Order.created_at.desc())

    async def get_for_customer(self, customer_id: UUID, order_id: UUID) -> Order | None:
        """
        Scoped to the customer as well as the tenant.

        Another customer's order id does not resolve, so it reads as "not
        found" -- which tells the caller nothing about whose order it is.
        """
        return await self.find_one(
            Order.id == order_id, Order.customer_id == customer_id
        )


class OrderItemRepository(TenantScopedRepository[OrderItem]):
    model = OrderItem
