from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select

from app.core.repository import TenantScopedRepository
from app.payments.constants import PaymentStatus
from app.payments.models import Payment


class PaymentRepository(TenantScopedRepository[Payment]):
    model = Payment

    def list_select(
        self,
        *,
        order_id: UUID | None = None,
        status: PaymentStatus | None = None,
    ) -> Select[tuple[Payment]]:
        stmt = self.base_select()

        if order_id is not None:
            stmt = stmt.where(Payment.order_id == order_id)

        if status is not None:
            stmt = stmt.where(Payment.status == status.value)

        return stmt.order_by(Payment.created_at.desc())

    async def get_by_status(self, order_id: UUID, status: PaymentStatus) -> Payment | None:
        """The order's payment in one particular state, if it has one."""
        return await self.find_one(
            Payment.order_id == order_id, Payment.status == status.value
        )
