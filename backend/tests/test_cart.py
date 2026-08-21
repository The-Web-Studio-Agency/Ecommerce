from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.cart.models import CartItem
from app.cart.schemas import CartItemCreate
from app.cart.service import CartService
from app.catalogue.serializers import sellable_quantity
from app.catalogue.service import InventoryService
from tests.conftest import headers_for
from tests.test_catalogue import PRODUCTS, make_category, make_product

CART = "/api/v1/cart"


async def make_variant(
    client, admin_headers, *, sku="TSH-BLK-M", price="999.00", quantity=10, status="ACTIVE"
) -> dict:
    """An ACTIVE variant on an ACTIVE product, with stock."""
    category = await make_category(client, admin_headers)
    product = await make_product(
        client, admin_headers, category["id"], name="T-Shirt", status="ACTIVE"
    )
    response = await client.post(
        f"{PRODUCTS}/{product['id']}/variants",
        json={
            "sku": sku,
            "name": "Black / M",
            "price": price,
            "status": status,
            "initial_quantity": quantity,
            "options": [{"name": "Color", "value": "Black"}, {"name": "Size", "value": "M"}],
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.fixture
async def customer(make_user, tenant):
    return await make_user(tenant=tenant, phone="+919811110001")


@pytest.fixture
def customer_auth(customer):
    return headers_for(customer)


async def add(client, headers, variant_id, quantity=1):
    return await client.post(
        f"{CART}/items", json={"variant_id": variant_id, "quantity": quantity}, headers=headers
    )


# ------------------------------- auth ---------------------------------------


async def test_an_unauthenticated_request_cannot_reach_the_cart(client, tenant):
    for method, path in (
        ("get", CART),
        ("post", f"{CART}/items"),
        ("delete", CART),
    ):
        response = await getattr(client, method)(path)
        assert response.status_code == 401, path


async def test_staff_cannot_use_the_customer_cart(client, staff_headers):
    response = await client.get(CART, headers=staff_headers)

    assert response.status_code == 403


# ------------------------------- basics -------------------------------------


async def test_an_empty_cart_is_created_on_first_view(client, customer_auth):
    response = await client.get(CART, headers=customer_auth)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["items"] == []
    assert body["subtotal"] == "0.00"
    assert body["item_count"] == 0


async def test_the_same_cart_is_returned_on_every_call(client, customer_auth):
    first = (await client.get(CART, headers=customer_auth)).json()["data"]
    second = (await client.get(CART, headers=customer_auth)).json()["data"]

    assert first["id"] == second["id"]


async def test_a_variant_can_be_added(client, admin_headers, customer_auth):
    variant = await make_variant(client, admin_headers)

    response = await add(client, customer_auth, variant["id"], 2)

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    item = body["items"][0]
    assert item["variant_id"] == variant["id"]
    assert item["product_name"] == "T-Shirt"
    assert item["variant_name"] == "Black / M"
    assert item["sku"] == "TSH-BLK-M"
    assert item["quantity"] == 2
    assert item["image"]["url"]
    assert body["item_count"] == 2


async def test_adding_the_same_variant_twice_increases_the_quantity(
    client, admin_headers, customer_auth
):
    variant = await make_variant(client, admin_headers)

    await add(client, customer_auth, variant["id"], 2)
    response = await add(client, customer_auth, variant["id"], 3)

    body = response.json()["data"]
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


async def test_quantity_can_be_updated(client, admin_headers, customer_auth):
    variant = await make_variant(client, admin_headers)
    item_id = (await add(client, customer_auth, variant["id"], 1)).json()["data"]["items"][0]["id"]

    response = await client.patch(
        f"{CART}/items/{item_id}", json={"quantity": 4}, headers=customer_auth
    )

    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["quantity"] == 4


async def test_an_item_can_be_removed(client, admin_headers, customer_auth):
    variant = await make_variant(client, admin_headers)
    item_id = (await add(client, customer_auth, variant["id"], 1)).json()["data"]["items"][0]["id"]

    response = await client.delete(f"{CART}/items/{item_id}", headers=customer_auth)

    assert response.status_code == 200
    assert response.json()["data"]["items"] == []


async def test_clearing_the_cart_empties_it_but_keeps_the_cart(
    client, admin_headers, customer_auth
):
    variant = await make_variant(client, admin_headers)
    cart_id = (await add(client, customer_auth, variant["id"], 2)).json()["data"]["id"]

    response = await client.delete(CART, headers=customer_auth)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["items"] == []
    assert body["id"] == cart_id


# ----------------------------- validation -----------------------------------


@pytest.mark.parametrize("quantity", [0, -1, -50])
async def test_quantity_must_be_at_least_one(
    client, admin_headers, customer_auth, quantity
):
    variant = await make_variant(client, admin_headers)

    response = await add(client, customer_auth, variant["id"], quantity)

    assert response.status_code == 422


async def test_an_unknown_variant_is_rejected(client, customer_auth):
    response = await add(client, customer_auth, str(uuid4()), 1)

    assert response.status_code == 404
    assert response.json()["message"] == "Product variant not found"


async def test_an_inactive_variant_is_rejected(client, admin_headers, customer_auth):
    variant = await make_variant(client, admin_headers, status="DRAFT")

    response = await add(client, customer_auth, variant["id"], 1)

    assert response.status_code == 409
    assert response.json()["message"] == "Product variant is not available"


async def test_an_inactive_product_is_rejected(client, admin_headers, customer_auth):
    variant = await make_variant(client, admin_headers)
    await client.delete(f"{PRODUCTS}/{variant['product_id']}", headers=admin_headers)

    response = await add(client, customer_auth, variant["id"], 1)

    assert response.status_code == 409
    # Archiving the product archives its variants, so the variant check fires first.
    assert response.json()["error"]["code"] == "CONFLICT"


async def test_insufficient_stock_is_rejected_with_the_available_count(
    client, admin_headers, customer_auth
):
    variant = await make_variant(client, admin_headers, quantity=3)

    response = await add(client, customer_auth, variant["id"], 5)

    assert response.status_code == 409
    assert response.json()["message"] == "Only 3 items are available"


async def test_stock_is_checked_against_the_combined_quantity(
    client, admin_headers, customer_auth
):
    """Two adds of 3 against 5 in stock must fail: the cart would hold 6."""
    variant = await make_variant(client, admin_headers, quantity=5)

    assert (await add(client, customer_auth, variant["id"], 3)).status_code == 201

    response = await add(client, customer_auth, variant["id"], 3)
    assert response.status_code == 409


async def test_updating_beyond_available_stock_is_rejected(
    client, admin_headers, customer_auth
):
    variant = await make_variant(client, admin_headers, quantity=4)
    item_id = (await add(client, customer_auth, variant["id"], 1)).json()["data"]["items"][0]["id"]

    response = await client.patch(
        f"{CART}/items/{item_id}", json={"quantity": 9}, headers=customer_auth
    )

    assert response.status_code == 409
    assert response.json()["message"] == "Only 4 items are available"
    # The quantity must not be silently reduced.
    cart = (await client.get(CART, headers=customer_auth)).json()["data"]
    assert cart["items"][0]["quantity"] == 1


# ------------------------------ ownership -----------------------------------


async def test_a_customer_cannot_touch_another_customers_item(
    client, admin_headers, customer_auth, make_user, tenant
):
    variant = await make_variant(client, admin_headers)
    item_id = (await add(client, customer_auth, variant["id"], 1)).json()["data"]["items"][0]["id"]

    intruder = headers_for(await make_user(tenant=tenant, phone="+919811110002"))

    assert (
        await client.patch(
            f"{CART}/items/{item_id}", json={"quantity": 5}, headers=intruder
        )
    ).status_code == 404
    assert (
        await client.delete(f"{CART}/items/{item_id}", headers=intruder)
    ).status_code == 404


async def test_carts_are_isolated_between_tenants(
    client, other_client, admin_headers, other_admin_headers, make_user, tenant, other_tenant
):
    variant = await make_variant(client, admin_headers)
    mine = headers_for(await make_user(tenant=tenant, phone="+919811110003"))
    theirs = headers_for(await make_user(tenant=other_tenant, phone="+919811110004"))

    await add(client, mine, variant["id"], 2)

    # Same token shape, different tenant: the other tenant's customer sees an
    # empty cart, and cannot add a variant that belongs to tenant A.
    other_cart = await other_client.get(CART, headers=theirs)
    assert other_cart.status_code == 200
    assert other_cart.json()["data"]["items"] == []

    assert (await add(other_client, theirs, variant["id"], 1)).status_code == 404


async def test_a_customers_token_is_rejected_on_another_tenants_host(
    client, other_client, make_user, tenant, other_tenant
):
    """A valid tenant-A token presented on tenant B's hostname is not accepted."""
    mine = headers_for(await make_user(tenant=tenant, phone="+919811110005"))

    response = await other_client.get(CART, headers=mine)

    assert response.status_code == 401


# ------------------------------- pricing ------------------------------------


async def test_the_subtotal_uses_the_database_price(client, admin_headers, customer_auth):
    variant = await make_variant(client, admin_headers, price="999.00")

    body = (await add(client, customer_auth, variant["id"], 2)).json()["data"]

    assert body["items"][0]["unit_price"] == "999.00"
    assert body["items"][0]["subtotal"] == "1998.00"
    assert body["subtotal"] == "1998.00"


async def test_a_price_sent_by_the_client_is_ignored(client, admin_headers, customer_auth):
    variant = await make_variant(client, admin_headers, price="999.00")

    response = await client.post(
        f"{CART}/items",
        json={
            "variant_id": variant["id"],
            "quantity": 1,
            "unit_price": "1.00",
            "subtotal": "1.00",
        },
        headers=customer_auth,
    )

    assert response.status_code == 201
    assert response.json()["data"]["items"][0]["unit_price"] == "999.00"


async def test_a_price_change_is_reflected_in_the_cart(
    client, admin_headers, customer_auth
):
    """Nothing is copied into the cart, so the new price shows immediately."""
    variant = await make_variant(client, admin_headers, price="999.00")
    await add(client, customer_auth, variant["id"], 1)

    await client.patch(
        f"/api/v1/catalogue/variants/{variant['id']}",
        json={"price": "1499.00"},
        headers=admin_headers,
    )

    body = (await client.get(CART, headers=customer_auth)).json()["data"]
    assert body["items"][0]["unit_price"] == "1499.00"


# ------------------------------ inventory -----------------------------------


async def test_adding_to_a_cart_does_not_reserve_stock(
    client, admin_headers, customer_auth, session, tenant
):
    variant = await make_variant(client, admin_headers, quantity=10)

    await add(client, customer_auth, variant["id"], 5)

    item = await InventoryService(session, tenant.id).get(UUID(variant["id"]))
    assert item.reserved_quantity == 0
    assert sellable_quantity(item) == 10


async def test_two_customers_may_hold_the_same_stock_in_their_carts(
    client, admin_headers, make_user, tenant
):
    variant = await make_variant(client, admin_headers, quantity=10)
    first = headers_for(await make_user(tenant=tenant, phone="+919811110006"))
    second = headers_for(await make_user(tenant=tenant, phone="+919811110007"))

    assert (await add(client, first, variant["id"], 8)).status_code == 201
    assert (await add(client, second, variant["id"], 8)).status_code == 201


# ----------------------------- concurrency ----------------------------------


async def test_adding_the_same_variant_concurrently_makes_one_line(
    engine, session, tenant, client, admin_headers, customer
):
    """
    The unique constraint on (cart_id, variant_id) is what is under test.

    Several sessions add the same variant at once; the database must allow only
    one row, and the losers must fold their quantity into it rather than error.
    """
    variant = await make_variant(client, admin_headers, quantity=50)
    variant_id = UUID(variant["id"])

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def add_one() -> str:
        async with factory() as own_session:
            service = CartService(own_session, tenant.id, customer.id)
            await service.add_item(CartItemCreate(variant_id=variant_id, quantity=1))
            return "added"

    results = await asyncio.gather(*[add_one() for _ in range(5)], return_exceptions=True)
    failures = [r for r in results if isinstance(r, Exception)]

    rows = await session.scalar(
        select(func.count())
        .select_from(CartItem)
        .where(CartItem.tenant_id == tenant.id, CartItem.variant_id == variant_id)
    )
    assert rows == 1, f"expected a single cart line, got {rows} ({failures})"
