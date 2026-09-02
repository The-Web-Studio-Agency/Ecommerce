from __future__ import annotations

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


async def _make_order(session: AsyncSession, tenant, customer, *, status: str, payment_status: str) -> Order:
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
