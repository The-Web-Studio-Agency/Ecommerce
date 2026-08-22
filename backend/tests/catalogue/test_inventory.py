from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.catalogue.service import InventoryService
from app.core.exceptions import ConflictError
from tests.helpers import PRODUCTS, make_category, make_product

INVENTORY = "/api/v1/catalogue/variants/{variant_id}/inventory"


async def make_stocked_variant(
    client, headers, product_id, *, sku="STOCK-1", quantity=10
) -> dict:
    response = await client.post(
        f"{PRODUCTS}/{product_id}/variants",
        json={
            "sku": sku,
            "name": "Standard",
            "price": "100.00",
            "status": "ACTIVE",
            "initial_quantity": quantity,
            "low_stock_threshold": 2,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.fixture
def inventory_url():
    return lambda variant_id: INVENTORY.format(variant_id=variant_id)


async def test_a_variant_gets_an_inventory_record_at_creation(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    variant = await make_stocked_variant(
        client, admin_headers, product["id"], quantity=7
    )

    assert variant["inventory"]["available_quantity"] == 7
    assert variant["inventory"]["reserved_quantity"] == 0
    assert variant["inventory"]["sellable_quantity"] == 7


async def test_stock_cannot_be_driven_negative(client, admin_headers, inventory_url):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_stocked_variant(client, admin_headers, product["id"], quantity=5)

    response = await client.post(
        f"{inventory_url(variant['id'])}/adjust",
        json={"delta": -6},
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"

    state = await client.get(inventory_url(variant["id"]), headers=admin_headers)
    assert state.json()["data"]["available_quantity"] == 5


async def test_stock_cannot_be_set_below_what_is_reserved(
    client, admin_headers, session, tenant, inventory_url
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_stocked_variant(client, admin_headers, product["id"], quantity=5)

    await InventoryService(session, tenant.id).reserve(UUID(variant["id"]), 3)

    response = await client.put(
        inventory_url(variant["id"]),
        json={"available_quantity": 1},
        headers=admin_headers,
    )

    assert response.status_code == 409


async def test_reservation_reduces_sellable_stock_without_moving_available(
    client, admin_headers, session, tenant, inventory_url
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_stocked_variant(client, admin_headers, product["id"], quantity=10)

    await InventoryService(session, tenant.id).reserve(UUID(variant["id"]), 4)

    state = (
        await client.get(inventory_url(variant["id"]), headers=admin_headers)
    ).json()["data"]

    assert state["available_quantity"] == 10
    assert state["reserved_quantity"] == 4
    assert state["sellable_quantity"] == 6


async def test_insufficient_stock_is_rejected(session, tenant, client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_stocked_variant(client, admin_headers, product["id"], quantity=2)

    service = InventoryService(session, tenant.id)

    with pytest.raises(ConflictError) as exc:
        await service.reserve(UUID(variant["id"]), 3)

    assert exc.value.error_code == "INSUFFICIENT_STOCK"


async def test_cancelling_an_order_releases_its_reservation(
    client, admin_headers, session, tenant, inventory_url
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_stocked_variant(client, admin_headers, product["id"], quantity=10)

    service = InventoryService(session, tenant.id)
    await service.reserve(UUID(variant["id"]), 4, reference="order-1")
    await service.release(UUID(variant["id"]), 4, reference="order-1")

    state = (
        await client.get(inventory_url(variant["id"]), headers=admin_headers)
    ).json()["data"]

    assert state["reserved_quantity"] == 0
    assert state["sellable_quantity"] == 10


async def test_fulfilment_removes_stock_and_clears_the_reservation(
    client, admin_headers, session, tenant, inventory_url
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_stocked_variant(client, admin_headers, product["id"], quantity=10)

    service = InventoryService(session, tenant.id)
    await service.reserve(UUID(variant["id"]), 3, reference="order-2")
    await service.fulfil(UUID(variant["id"]), 3, reference="order-2")

    state = (
        await client.get(inventory_url(variant["id"]), headers=admin_headers)
    ).json()["data"]

    assert state["available_quantity"] == 7
    assert state["reserved_quantity"] == 0


async def test_every_stock_change_is_recorded_as_a_movement(
    client, admin_headers, inventory_url
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_stocked_variant(client, admin_headers, product["id"], quantity=5)

    await client.post(
        f"{inventory_url(variant['id'])}/adjust",
        json={"delta": 3, "reason": "RESTOCK", "reference": "po-9"},
        headers=admin_headers,
    )

    movements = (
        await client.get(
            f"{inventory_url(variant['id'])}/movements", headers=admin_headers
        )
    ).json()

    reasons = [m["reason"] for m in movements["data"]]
    assert "RESTOCK" in reasons
    assert "INITIAL" in reasons


async def test_concurrent_reservations_never_oversell(
    engine, session, tenant, client, admin_headers
):
    """
    The invariant that matters: demand above stock must be partly refused.

    Each task runs on its own session, so this exercises the conditional UPDATE
    against real concurrent transactions rather than one serialised session.
    """
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_stocked_variant(client, admin_headers, product["id"], quantity=10)
    variant_id = UUID(variant["id"])

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def reserve_two() -> str:
        async with factory() as own_session:
            try:
                await InventoryService(own_session, tenant.id).reserve(variant_id, 2)
                return "granted"
            except ConflictError:
                return "refused"

    results = await asyncio.gather(*[reserve_two() for _ in range(8)])

    # 10 units, 2 per request -> exactly five can succeed, no matter the order.
    assert results.count("granted") == 5
    assert results.count("refused") == 3

    state = await InventoryService(session, tenant.id).get(variant_id)
    assert state.reserved_quantity == 10
    assert state.reserved_quantity <= state.available_quantity


async def test_inventory_of_another_tenants_variant_is_not_found(
    client, other_client, admin_headers, other_admin_headers, inventory_url
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_stocked_variant(client, admin_headers, product["id"])

    response = await other_client.get(
        inventory_url(variant["id"]), headers=other_admin_headers
    )

    assert response.status_code == 404


async def test_variants_carry_structured_options(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    response = await client.post(
        f"{PRODUCTS}/{product['id']}/variants",
        json={
            "sku": "TSH-BLK-M",
            "name": "M / Black",
            "price": "999.00",
            "status": "ACTIVE",
            "options": [
                {"name": "Color", "value": "Black"},
                {"name": "Size", "value": "M"},
            ],
            "initial_quantity": 4,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["data"]["options"] == {"Color": "Black", "Size": "M"}


async def test_an_option_name_cannot_repeat_within_one_variant(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    response = await client.post(
        f"{PRODUCTS}/{product['id']}/variants",
        json={
            "sku": "DUP-1",
            "name": "Duplicate",
            "price": "10.00",
            "options": [
                {"name": "Size", "value": "M"},
                {"name": "Size", "value": "L"},
            ],
        },
        headers=admin_headers,
    )

    assert response.status_code == 422


async def test_option_names_are_shared_across_a_products_variants(
    client, admin_headers, session, tenant
):
    """Two variants naming "Color" must reuse one option row, not create two."""
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    for sku, colour in (("OPT-1", "Black"), ("OPT-2", "Ivory")):
        await client.post(
            f"{PRODUCTS}/{product['id']}/variants",
            json={
                "sku": sku,
                "name": colour,
                "price": "10.00",
                "status": "ACTIVE",
                "options": [{"name": "Color", "value": colour}],
            },
            headers=admin_headers,
        )

    detail = await client.get(f"{PRODUCTS}/{product['id']}", headers=admin_headers)
    options = detail.json()["data"]["options"]

    assert [option["name"] for option in options] == ["Color"]
