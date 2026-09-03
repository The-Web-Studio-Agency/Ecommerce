from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.orders.constants import OrderStatus
from app.orders.models import Order, OrderItem
from app.payments.constants import PaymentStatus
from app.payments.models import Payment


def _delivery_fields() -> dict:
    """Required, non-catalogue fields every Order row needs."""
    return {
        "delivery_name": "Dashboard Tester",
        "delivery_phone": "+919876500000",
        "delivery_address_line_1": "1 Test Street",
        "delivery_city": "Testville",
        "delivery_state": "TS",
        "delivery_postal_code": "100001",
        "delivery_country": "IN",
    }


async def _make_order(
    session: AsyncSession,
    tenant,
    customer,
    *,
    status: str,
    payment_status: str,
    created_at: datetime | None = None,
) -> Order:
    subtotal = Decimal("100.00")
    order = Order(
        tenant_id=tenant.id,
        customer_id=customer.id,
        order_number=f"ORD-{uuid4().hex[:10].upper()}",
        status=status,
        payment_status=payment_status,
        subtotal=subtotal,
        shipping_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=subtotal,
        **_delivery_fields(),
    )
    if created_at is not None:
        order.created_at = created_at
    session.add(order)
    await session.flush()
    return order


@pytest.mark.asyncio
async def test_dashboard_authorization_guards(client: AsyncClient, customer_headers: dict):
    # Customer should be forbidden from accessing admin dashboard
    response = await client.get("/api/v1/admin/dashboard", headers=customer_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_dashboard_overview_success(
    client: AsyncClient,
    admin_headers: dict,
    session: AsyncSession,
    tenant,
    make_user,
    variant,
    new_variant,
):
    customer = await make_user(tenant=tenant)

    # A near-empty variant to trigger the low-stock overview.
    low_stock_variant = await new_variant(initial_quantity=2, low_stock_threshold=5)

    order = await _make_order(
        session, tenant, customer, status=OrderStatus.PROCESSING, payment_status=PaymentStatus.PAID
    )
    item = OrderItem(
        tenant_id=tenant.id,
        order_id=order.id,
        variant_id=variant["id"],
        product_id=variant["product_id"],
        product_name="Dashboard Widget",
        variant_name=variant["name"],
        sku=variant["sku"],
        unit_price=Decimal("100.00"),
        quantity=1,
        subtotal=Decimal("100.00"),
    )
    session.add(item)

    payment = Payment(
        tenant_id=tenant.id,
        order_id=order.id,
        amount=Decimal("100.00"),
        status=PaymentStatus.PAID,
    )
    session.add(payment)
    await session.commit()

    response = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["sales"]["today"]["order_count"] >= 1
    assert Decimal(data["sales"]["today"]["revenue"]) >= Decimal("100.00")
    assert data["orders"]["total"] >= 1
    assert data["orders"]["today"] >= 1
    assert data["orders"]["processing"] >= 1
    assert data["products"]["total"] >= 1
    assert data["inventory"]["low_stock_count"] >= 1
    assert any(p["sku"] == low_stock_variant["sku"] for p in data["inventory"]["low_stock_products"])
    assert data["payments"]["paid_count"] >= 1
    assert len(data["recent_orders"]) >= 1


@pytest.mark.asyncio
async def test_dashboard_counts_returned_orders_from_refunded_payments(
    client: AsyncClient,
    admin_headers: dict,
    session: AsyncSession,
    tenant,
    make_user,
):
    """There is no RETURNED order status -- a refunded payment is the signal."""
    customer = await make_user(tenant=tenant)

    order = await _make_order(
        session, tenant, customer, status=OrderStatus.DELIVERED, payment_status=PaymentStatus.REFUNDED
    )
    payment = Payment(
        tenant_id=tenant.id,
        order_id=order.id,
        amount=Decimal("100.00"),
        status=PaymentStatus.REFUNDED,
    )
    session.add(payment)
    await session.commit()

    response = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["orders"]["returned"] >= 1
    assert data["orders"]["total"] >= 1
    assert data["payments"]["refunded_count"] >= 1


@pytest.mark.asyncio
async def test_dashboard_sales_trend_and_top_products(
    client: AsyncClient,
    staff_headers: dict,
    session: AsyncSession,
    tenant,
    make_user,
    variant,
):
    customer = await make_user(tenant=tenant)

    order = await _make_order(
        session, tenant, customer, status=OrderStatus.DELIVERED, payment_status=PaymentStatus.PAID
    )
    item = OrderItem(
        tenant_id=tenant.id,
        order_id=order.id,
        variant_id=variant["id"],
        product_id=variant["product_id"],
        product_name="Summer Dress",
        variant_name=variant["name"],
        sku=variant["sku"],
        unit_price=Decimal("50.00"),
        quantity=3,
        subtotal=Decimal("150.00"),
    )
    session.add(item)
    await session.commit()

    trend_res = await client.get("/api/v1/admin/dashboard/sales-trend?days=7", headers=staff_headers)
    assert trend_res.status_code == 200, trend_res.text
    assert len(trend_res.json()["data"]) >= 1

    top_res = await client.get("/api/v1/admin/dashboard/top-products?days=7&limit=5", headers=staff_headers)
    assert top_res.status_code == 200, top_res.text
    top_items = top_res.json()["data"]
    assert len(top_items) >= 1
    # Product.name is what get_top_products groups by -- "Summer Dress" is
    # catalogue's default product sample name (see tests/catalogue/data.json).
    assert top_items[0]["product_name"] == "Summer Dress"
    assert top_items[0]["quantity_sold"] == 3


@pytest.mark.asyncio
async def test_todays_orders_counts_every_status_but_sales_today_stays_completed_only(
    client: AsyncClient,
    admin_headers: dict,
    session: AsyncSession,
    tenant,
    make_user,
):
    """orders.today counts all orders placed today regardless of status;
    sales.today.order_count must stay unchanged -- completed sales only."""
    customer = await make_user(tenant=tenant)

    # PENDING/unpaid -- not a "completed sale", but still placed today.
    await _make_order(
        session, tenant, customer, status=OrderStatus.PENDING, payment_status=PaymentStatus.PENDING
    )
    await session.commit()

    response = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["orders"]["today"] >= 1
    assert data["sales"]["today"]["order_count"] == 0


@pytest.mark.asyncio
async def test_week_over_week_comparison_calculates_counts_revenue_and_pct(
    client: AsyncClient,
    admin_headers: dict,
    session: AsyncSession,
    tenant,
    make_user,
):
    customer = await make_user(tenant=tenant)
    now = datetime.now(timezone.utc)

    # Current week window (last 7 days): two completed orders, 100.00 each.
    for _ in range(2):
        await _make_order(
            session,
            tenant,
            customer,
            status=OrderStatus.DELIVERED,
            payment_status=PaymentStatus.PAID,
            created_at=now - timedelta(days=2),
        )

    # Previous week window (7-14 days ago): one completed order, 100.00.
    await _make_order(
        session,
        tenant,
        customer,
        status=OrderStatus.DELIVERED,
        payment_status=PaymentStatus.PAID,
        created_at=now - timedelta(days=9),
    )
    await session.commit()

    response = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200, response.text
    week = response.json()["data"]["sales"]["week"]

    assert week["order_count"] >= 2
    assert week["previous_order_count"] >= 1
    assert Decimal(week["revenue"]) >= Decimal("200.00")
    assert Decimal(week["previous_revenue"]) >= Decimal("100.00")
    # 2 vs 1 -> +100%; both figures are computed the same way sales.month
    # already does, reusing PeriodMetric's change-pct fields.
    assert week["order_count_change_pct"] == round(
        (week["order_count"] - week["previous_order_count"]) / week["previous_order_count"] * 100.0, 2
    )
    assert week["revenue_change_pct"] == round(
        (float(week["revenue"]) - float(week["previous_revenue"]))
        / float(week["previous_revenue"])
        * 100.0,
        2,
    )
