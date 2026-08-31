from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_customer, require_staff
from app.core.database import get_db
from app.core.pagination import PageParams, page_params
from app.core.responses import ApiResponse, ok, paginated
from app.payments.constants import PaymentStatus
from app.payments.schemas import PaymentRead
from app.payments.serializers import payment_read
from app.payments.service import PaymentService
from app.tenants.resolver import CurrentTenant
from app.users.models import User

router = APIRouter(prefix="/payments", tags=["Payments"])

admin_router = APIRouter(prefix="/admin/payments", tags=["Admin-Payments"])


@router.get(
    "/{payment_id}",
    response_model=ApiResponse[PaymentRead],
    summary="Retrieve one of your payments",
)
async def get_my_payment(
    payment_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[PaymentRead]:
    payment = await PaymentService(session, user.tenant_id).get_for_customer(
        user.id, payment_id
    )
    return ok(payment_read(payment, tenant.currency), message="Payment retrieved")


@admin_router.get(
    "",
    response_model=ApiResponse[list[PaymentRead]],
    summary="List payments",
)
async def list_payments(
    tenant: CurrentTenant,
    order_id: UUID | None = Query(default=None, description="Payments for one order"),
    payment_status: PaymentStatus | None = Query(default=None, alias="status"),
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[list[PaymentRead]]:
    payments, total = await PaymentService(session, user.tenant_id).list(
        params, order_id=order_id, status=payment_status
    )
    return paginated(
        [payment_read(payment, tenant.currency) for payment in payments],
        total_items=total,
        params=params,
        message="Payments retrieved",
    )


@admin_router.get(
    "/{payment_id}",
    response_model=ApiResponse[PaymentRead],
    summary="Retrieve a payment",
)
async def get_payment(
    payment_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[PaymentRead]:
    payment = await PaymentService(session, user.tenant_id).get(payment_id)
    return ok(payment_read(payment, tenant.currency), message="Payment retrieved")
