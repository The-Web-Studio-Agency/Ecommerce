"""Fixtures for search, sort, and filter tests."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from app.orders.constants import OrderStatus
from app.orders.models import Order, OrderItem
from app.payments.constants import PaymentStatus
from app.ratings.models import Review
from tests.catalogue.factories import make_category, make_product
from tests.conftest import headers_for
from tests.helpers import load_data, sample

DATA = load_data(__file__)

SEARCH = DATA["routes"]["search"]
PRODUCTS = DATA["routes"]["products"]


@pytest_asyncio.fixture(loop_scope="session")
async def search_shopper(make_user, tenant):
    return await make_user(tenant=tenant, phone="+919822224001")


@pytest.fixture
def search_auth(search_shopper) -> dict[str, str]:
    return headers_for(search_shopper)


@pytest_asyncio.fixture(loop_scope="session")
async def search_test_catalogue(client, admin_headers):
    """Sets up a diverse catalogue for testing search, sort, and filters.

    Each product carries distinct Gender/Color/Size options so attribute
    filters have real, non-overlapping data to match against.
    """
    category = await make_category(client, admin_headers, name="Apparel")

    product_data = [
        {
            "name": "Running Sneaker",
            "price": "1499.00",
            "brand": "Nike",
            "options": [
                {"name": "Gender", "value": "Male"},
                {"name": "Color", "value": "Black"},
                {"name": "Size", "value": "M"},
            ],
        },
        {
            "name": "Cotton T-Shirt",
            "price": "499.00",
            "brand": "Puma",
            "options": [
                {"name": "Gender", "value": "Female"},
                {"name": "Color", "value": "White"},
                {"name": "Size", "value": "S"},
            ],
        },
        {
            "name": "Formal Shirt",
            "price": "999.00",
            "brand": "Adidas",
            "options": [
                {"name": "Gender", "value": "Unisex"},
                {"name": "Color", "value": "Blue"},
                {"name": "Size", "value": "L"},
            ],
        },
    ]

    created = {}
    for item in product_data:
        prod = await make_product(
            client, admin_headers, category["id"], name=item["name"], status="ACTIVE", brand=item["brand"]
        )
        payload = sample(DATA, "variant")
        payload["sku"] = f"SRCH-SKU-{item['name'][:3].upper()}"
        payload["price"] = item["price"]
        payload["options"] = item["options"]
        response = await client.post(
            f"{PRODUCTS}/{prod['id']}/variants", json=payload, headers=admin_headers
        )
        assert response.status_code == 201, response.text
        variant = response.json()["data"]
        created[item["name"]] = {"product": prod, "variant": variant}

    return created


@pytest_asyncio.fixture(loop_scope="session")
async def search_multi_variant_product(client, admin_headers):
    """One product with three variants across two colors and two sizes:

    Color=Black/Size=S, Color=Black/Size=M, Color=Green/Size=S

    Isolated from search_test_catalogue's single-variant products so
    multi-variant assertions can't interfere with their price/rating tests.
    """
    category = await make_category(client, admin_headers, name="Multi-Variant Apparel")
    product = await make_product(
        client, admin_headers, category["id"], name="Graphic Hoodie", status="ACTIVE", brand="Zeen"
    )

    combos = [
        ("Black", "S", "HOODIE-BLK-S"),
        ("Black", "M", "HOODIE-BLK-M"),
        ("Green", "S", "HOODIE-GRN-S"),
    ]
    variants = []
    for color, size, sku in combos:
        payload = sample(DATA, "variant")
        payload["sku"] = sku
        payload["options"] = [
            {"name": "Color", "value": color},
            {"name": "Size", "value": size},
        ]
        response = await client.post(
            f"{PRODUCTS}/{product['id']}/variants", json=payload, headers=admin_headers
        )
        assert response.status_code == 201, response.text
        variants.append(response.json()["data"])

    return {"product": product, "variants": variants}


@pytest_asyncio.fixture(loop_scope="session")
async def search_ratings_and_orders(session, tenant, search_shopper, make_user, search_test_catalogue):
    """Gives the fixture catalogue real ratings and order history:

    - Cotton T-Shirt: reviews averaging 4.0, most popular (5 units ordered)
    - Formal Shirt: reviews averaging 2.0, some popularity (2 units ordered)
    - Running Sneaker: no reviews at all, no orders (least popular)
    """
    catalogue = search_test_catalogue

    # A second reviewer: one review per (user, product) is enforced at the
    # database level, so averaging two ratings on the same product needs two
    # distinct users.
    second_reviewer = await make_user(tenant=tenant, phone="+919822224002")

    reviews = [
        (catalogue["Cotton T-Shirt"]["product"]["id"], search_shopper.id, 5),
        (catalogue["Cotton T-Shirt"]["product"]["id"], second_reviewer.id, 3),
        (catalogue["Formal Shirt"]["product"]["id"], search_shopper.id, 2),
    ]
    for product_id, user_id, rating in reviews:
        session.add(
            Review(
                tenant_id=tenant.id,
                product_id=product_id,
                user_id=user_id,
                rating=rating,
                is_verified_purchase=True,
                is_approved=True,
            )
        )
    await session.commit()

    async def _place_order(item_name: str, quantity: int, order_status: str) -> None:
        variant = catalogue[item_name]["variant"]
        product = catalogue[item_name]["product"]
        unit_price = Decimal(str(variant["price"]))
        subtotal = unit_price * quantity

        order = Order(
            tenant_id=tenant.id,
            customer_id=search_shopper.id,
            order_number=f"ORD-{uuid4().hex[:10].upper()}",
            status=order_status,
            payment_status=PaymentStatus.PAID.value,
            subtotal=subtotal,
            shipping_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=subtotal,
            delivery_name="Search Tester",
            delivery_phone="+919876500002",
            delivery_address_line_1="1 Test Street",
            delivery_city="Testville",
            delivery_state="TS",
            delivery_postal_code="100001",
            delivery_country="IN",
        )
        session.add(order)
        await session.flush()

        session.add(
            OrderItem(
                tenant_id=tenant.id,
                order_id=order.id,
                variant_id=variant["id"],
                product_id=product["id"],
                product_name=product["name"],
                variant_name=variant["name"],
                sku=variant["sku"],
                unit_price=unit_price,
                quantity=quantity,
                subtotal=subtotal,
            )
        )
        await session.commit()

    await _place_order("Cotton T-Shirt", 5, OrderStatus.DELIVERED.value)
    await _place_order("Formal Shirt", 2, OrderStatus.DELIVERED.value)
    # A cancelled order for the Sneaker must NOT count toward its popularity.
    await _place_order("Running Sneaker", 10, OrderStatus.CANCELLED.value)

    return catalogue
