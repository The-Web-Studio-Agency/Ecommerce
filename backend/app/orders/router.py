from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_customer, require_staff
from app.core.database import get_db
from app.core.pagination import PageParams, page_params
from app.core.responses import ApiResponse, ok, paginated
from app.orders.constants import OrderStatus, PaymentStatus
from app.orders.schemas import (
    CheckoutCreate,
    CheckoutPreview,
    OrderRead,
    OrderStatusUpdate,
    OrderSummaryRead,
)
from app.orders.serializers import order_read, order_summary_read
from app.orders.service import CheckoutService, OrderService
from app.tenants.resolver import CurrentTenant
from app.users.models import User

checkout_router = APIRouter(prefix="/checkout", tags=["Checkout"])

router = APIRouter(prefix="/orders", tags=["Orders"])

admin_router = APIRouter(prefix="/admin/orders", tags=["Admin-Order_management"])


@checkout_router.post(
    "/preview",
    response_model=ApiResponse[CheckoutPreview],
    summary="Price the cart before ordering",
)
async def preview_checkout(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[CheckoutPreview]:
    preview = await CheckoutService(session, user.tenant_id, user.id).preview()
    return ok(preview, message="Checkout preview")


@checkout_router.post(
    "",
    response_model=ApiResponse[OrderRead],
    status_code=status.HTTP_201_CREATED,
    summary="Place the order",
)
async def place_order(
    data: CheckoutCreate,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[OrderRead]:
    order = await CheckoutService(session, user.tenant_id, user.id).place_order(
        data.address_id
    )
    return ok(order_read(order, tenant.currency), message="Order placed")


@router.get(
    "",
    response_model=ApiResponse[list[OrderSummaryRead]],
    summary="List your orders",
)
async def list_my_orders(
    tenant: CurrentTenant,
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[list[OrderSummaryRead]]:
    orders, total = await OrderService(session, user.tenant_id).list(
        params, customer_id=user.id
    )
    return paginated(
        [order_summary_read(order, tenant.currency) for order in orders],
        total_items=total,
        params=params,
        message="Orders retrieved",
    )


@router.post(
    "/{order_id}/cancel",
    response_model=ApiResponse[OrderRead],
    summary="Cancel one of your orders",
)
async def cancel_my_order(
    order_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[OrderRead]:
    order = await OrderService(session, user.tenant_id).cancel_for_customer(
        user.id, order_id
    )
    return ok(order_read(order, tenant.currency), message="Order cancelled")


@router.get(
    "/{order_id}",
    response_model=ApiResponse[OrderRead],
    summary="Retrieve one of your orders",
)
async def get_my_order(
    order_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[OrderRead]:
    order = await OrderService(session, user.tenant_id).get_for_customer(
        user.id, order_id
    )
    return ok(order_read(order, tenant.currency), message="Order retrieved")


@admin_router.get(
    "",
    response_model=ApiResponse[list[OrderSummaryRead]],
    summary="List orders",
)
async def list_orders(
    tenant: CurrentTenant,
    order_number: str | None = Query(
        default=None, max_length=32, description="Match an order number"
    ),
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    payment_status: PaymentStatus | None = Query(default=None),
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[list[OrderSummaryRead]]:
    orders, total = await OrderService(session, user.tenant_id).list(
        params,
        order_number=order_number,
        status=order_status,
        payment_status=payment_status,
    )
    return paginated(
        [order_summary_read(order, tenant.currency) for order in orders],
        total_items=total,
        params=params,
        message="Orders retrieved",
    )


@admin_router.get(
    "/{order_id}",
    response_model=ApiResponse[OrderRead],
    summary="Retrieve an order",
)
async def get_order(
    order_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[OrderRead]:
    order = await OrderService(session, user.tenant_id).get(order_id)
    return ok(order_read(order, tenant.currency), message="Order retrieved")


@admin_router.patch(
    "/{order_id}/status",
    response_model=ApiResponse[OrderRead],
    summary="Move an order to its next status",
)
async def update_order_status(
    order_id: UUID,
    data: OrderStatusUpdate,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[OrderRead]:
    order = await OrderService(session, user.tenant_id).update_status(
        order_id, data.status
    )
    return ok(order_read(order, tenant.currency), message="Order status updated")
