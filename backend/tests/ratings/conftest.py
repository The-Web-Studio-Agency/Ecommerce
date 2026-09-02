"""
Fixtures for the ratings and reviews tests.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from app.orders.constants import OrderStatus
from app.orders.models import Order, OrderItem
from app.payments.constants import PaymentStatus
from tests.catalogue.factories import make_category, make_product, make_variant
from tests.conftest import headers_for
from tests.helpers import load_data, sample

DATA = load_data(__file__)

REVIEWS = DATA["routes"]["reviews"]
CUSTOMERS = DATA["customers"]


@pytest_asyncio.fixture(loop_scope="session")
async def customer(make_user, tenant):
    return await make_user(tenant=tenant, phone=CUSTOMERS["owner"])


@pytest.fixture
def customer_auth(customer) -> dict[str, str]:
    return headers_for(customer)


@pytest_asyncio.fixture(loop_scope="session")
async def reviewed_product(client, admin_headers):
    """Creates a product that can be used for reviews."""
    category = await make_category(client, admin_headers)
    product = await make_product(
        client,
        admin_headers,
        category["id"],
        name="Reviewable Product",
        status="ACTIVE",
    )
    return product


@pytest.fixture
def review_payload():
    return sample(DATA, "review")


@pytest_asyncio.fixture(loop_scope="session")
async def deliver_purchase(client, admin_headers, session, tenant):
    """Factory: `order = await deliver_purchase(customer, product)`.

    Inserts a DELIVERED order for that customer/product directly, so
    `check_user_purchased_product`/`get_delivered_order_id` finds it without
    driving a whole real checkout flow through the API.
    """

    async def _make(customer, product: dict) -> Order:
        # A unique SKU per call: this factory may be invoked more than once
        # for the same product (e.g. two different customers reviewing it),
        # and the default sample payload's SKU would otherwise collide.
        variant = await make_variant(
            client, admin_headers, product["id"], sku=f"SKU-{uuid4().hex[:12].upper()}"
        )

        subtotal = Decimal("100.00")
        order = Order(
            tenant_id=tenant.id,
            customer_id=customer.id,
            order_number=f"ORD-{uuid4().hex[:10].upper()}",
            status=OrderStatus.DELIVERED,
            payment_status=PaymentStatus.PAID,
            subtotal=subtotal,
            shipping_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=subtotal,
            delivery_name="Review Tester",
            delivery_phone="+919876500001",
            delivery_address_line_1="1 Test Street",
            delivery_city="Testville",
            delivery_state="TS",
            delivery_postal_code="100001",
            delivery_country="IN",
        )
        session.add(order)
        await session.flush()

        item = OrderItem(
            tenant_id=tenant.id,
            order_id=order.id,
            variant_id=variant["id"],
            product_id=product["id"],
            product_name=product["name"],
            variant_name=variant["name"],
            sku=variant["sku"],
            unit_price=subtotal,
            quantity=1,
            subtotal=subtotal,
        )
        session.add(item)
        await session.commit()
        return order

    return _make