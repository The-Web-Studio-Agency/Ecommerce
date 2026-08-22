from __future__ import annotations

import pytest

from tests.helpers import CATEGORIES, PRODUCTS, make_category, make_product

STOREFRONT = "/api/v1/storefront"


async def publish(
    client,
    headers,
    *,
    name="Linen Shirt",
    brand="Zeen",
    price="1000.00",
    featured=False,
    category=None,
    sku=None,
    quantity=5,
    options=None,
) -> dict:
    """Create an ACTIVE product with one ACTIVE, stocked variant."""
    category = category or await make_category(client, headers)
    product = await make_product(
        client,
        headers,
        category["id"],
        name=name,
        brand=brand,
        status="ACTIVE",
        is_featured=featured,
    )
    response = await client.post(
        f"{PRODUCTS}/{product['id']}/variants",
        json={
            "sku": sku or f"{name.replace(' ', '-').upper()}-1",
            "name": "Standard",
            "price": price,
            "status": "ACTIVE",
            "initial_quantity": quantity,
            "options": options or [{"name": "Color", "value": "Black"}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return product


async def test_only_active_products_are_public(client, admin_headers):
    live = await publish(client, admin_headers, name="Live Shirt")
    category = await make_category(client, admin_headers, name="Drafts")
    draft = await make_product(client, admin_headers, category["id"], name="Draft Shirt")

    listed = await client.get(f"{STOREFRONT}/products")
    names = [product["name"] for product in listed.json()["data"]]

    assert "Live Shirt" in names
    assert "Draft Shirt" not in names

    assert (await client.get(f"{STOREFRONT}/products/{draft['id']}")).status_code == 404
    assert (await client.get(f"{STOREFRONT}/products/{live['id']}")).status_code == 200


async def test_an_archived_product_disappears_from_the_storefront(client, admin_headers):
    product = await publish(client, admin_headers, name="Soon Gone")

    await client.delete(f"{PRODUCTS}/{product['id']}", headers=admin_headers)

    assert (
        await client.get(f"{STOREFRONT}/products/{product['id']}")
    ).status_code == 404


async def test_archiving_a_category_hides_its_products(client, admin_headers):
    category = await make_category(client, admin_headers, name="Seasonal")
    product = await publish(client, admin_headers, name="Seasonal Coat", category=category)

    # Archive the product first so the category is allowed to go.
    await client.delete(f"{PRODUCTS}/{product['id']}", headers=admin_headers)
    await client.delete(f"{CATEGORIES}/{category['id']}", headers=admin_headers)

    assert (
        await client.get(f"{STOREFRONT}/categories/{category['id']}")
    ).status_code == 404


async def test_the_storefront_never_leaks_internal_fields(client, admin_headers):
    product = await publish(client, admin_headers, name="Clean Payload")

    body = (await client.get(f"{STOREFRONT}/products/{product['id']}")).json()["data"]

    for leaked in ("tenant_id", "status", "created_at", "updated_at"):
        assert leaked not in body, leaked
    for variant in body["variants"]:
        assert "tenant_id" not in variant
        assert "reserved_quantity" not in variant


async def test_product_detail_carries_options_variants_and_stock(client, admin_headers):
    product = await publish(
        client,
        admin_headers,
        name="Option Tee",
        quantity=3,
        options=[{"name": "Color", "value": "Black"}, {"name": "Size", "value": "M"}],
    )

    body = (await client.get(f"{STOREFRONT}/products/{product['id']}")).json()["data"]

    assert body["category"]["name"]
    assert body["options"] == [
        {"name": "Color", "values": ["Black"]},
        {"name": "Size", "values": ["M"]},
    ]
    assert body["variants"][0]["options"] == {"Color": "Black", "Size": "M"}
    assert body["variants"][0]["available_quantity"] == 3
    assert body["in_stock"] is True


async def test_a_product_with_no_stock_reports_out_of_stock(client, admin_headers):
    product = await publish(client, admin_headers, name="Sold Out", quantity=0)

    body = (await client.get(f"{STOREFRONT}/products/{product['id']}")).json()["data"]

    assert body["in_stock"] is False
    assert body["variants"][0]["in_stock"] is False


async def test_the_listing_is_lightweight(client, admin_headers):
    await publish(client, admin_headers, name="Grid Item")

    row = (await client.get(f"{STOREFRONT}/products")).json()["data"][0]

    assert "primary_image" in row
    assert "price_from" in row
    # The heavy relations belong to the detail endpoint, not the grid.
    assert "variants" not in row
    assert "images" not in row


async def test_featured_products_can_be_filtered(client, admin_headers):
    await publish(client, admin_headers, name="Plain One", featured=False)
    await publish(client, admin_headers, name="Hero One", featured=True, sku="HERO-1")

    body = (
        await client.get(f"{STOREFRONT}/products", params={"featured": "true"})
    ).json()

    assert body["meta"]["total_items"] == 1
    assert body["data"][0]["name"] == "Hero One"


async def test_products_can_be_searched_by_name_and_brand(client, admin_headers):
    await publish(client, admin_headers, name="Merino Scarf", brand="Zeen")
    await publish(client, admin_headers, name="Cotton Cap", brand="Northbound", sku="CC-1")

    by_name = await client.get(f"{STOREFRONT}/products", params={"search": "merino"})
    assert [p["name"] for p in by_name.json()["data"]] == ["Merino Scarf"]

    by_brand = await client.get(f"{STOREFRONT}/products", params={"search": "northbound"})
    assert [p["name"] for p in by_brand.json()["data"]] == ["Cotton Cap"]


async def test_a_search_wildcard_is_not_treated_as_a_pattern(client, admin_headers):
    await publish(client, admin_headers, name="Regular Item")

    response = await client.get(f"{STOREFRONT}/products", params={"search": "%"})

    assert response.status_code == 200
    assert response.json()["meta"]["total_items"] == 0


async def test_products_can_be_filtered_by_price_range(client, admin_headers):
    await publish(client, admin_headers, name="Cheap", price="100.00", sku="CHEAP-1")
    await publish(client, admin_headers, name="Pricey", price="5000.00", sku="PRICEY-1")

    cheap = await client.get(f"{STOREFRONT}/products", params={"max_price": "1000"})
    assert [p["name"] for p in cheap.json()["data"]] == ["Cheap"]

    pricey = await client.get(f"{STOREFRONT}/products", params={"min_price": "1000"})
    assert [p["name"] for p in pricey.json()["data"]] == ["Pricey"]


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("price_low", ["Alpha", "Beta"]),
        ("price_high", ["Beta", "Alpha"]),
        ("name_asc", ["Alpha", "Beta"]),
        ("name_desc", ["Beta", "Alpha"]),
    ],
)
async def test_products_can_be_sorted(client, admin_headers, sort, expected):
    await publish(client, admin_headers, name="Alpha", price="100.00", sku="ALPHA-1")
    await publish(client, admin_headers, name="Beta", price="900.00", sku="BETA-1")

    body = await client.get(f"{STOREFRONT}/products", params={"sort": sort})

    assert [p["name"] for p in body.json()["data"]] == expected


async def test_an_unknown_sort_is_rejected(client, admin_headers):
    response = await client.get(f"{STOREFRONT}/products", params={"sort": "'; DROP--"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_the_listing_paginates(client, admin_headers):
    category = await make_category(client, admin_headers)
    for index in range(5):
        await publish(
            client,
            admin_headers,
            name=f"Item {index}",
            category=category,
            sku=f"PAGE-{index}",
        )

    page = await client.get(
        f"{STOREFRONT}/products", params={"page": 2, "page_size": 2, "sort": "name_asc"}
    )
    body = page.json()

    assert body["meta"]["total_items"] == 5
    assert body["meta"]["total_pages"] == 3
    assert len(body["data"]) == 2
    assert [p["name"] for p in body["data"]] == ["Item 2", "Item 3"]


async def test_the_storefront_serves_the_tenant_that_owns_the_hostname(
    client, other_client, admin_headers, other_admin_headers
):
    await publish(client, admin_headers, name="Zeen Only")
    await publish(other_client, other_admin_headers, name="Acme Only", sku="ACME-1")

    zeen = [p["name"] for p in (await client.get(f"{STOREFRONT}/products")).json()["data"]]
    acme = [
        p["name"] for p in (await other_client.get(f"{STOREFRONT}/products")).json()["data"]
    ]

    assert zeen == ["Zeen Only"]
    assert acme == ["Acme Only"]


async def test_a_product_id_from_another_tenant_is_not_found(
    client, other_client, admin_headers, other_admin_headers
):
    product = await publish(client, admin_headers, name="Zeen Private")

    response = await other_client.get(f"{STOREFRONT}/products/{product['id']}")

    assert response.status_code == 404


async def test_the_storefront_needs_no_authentication(client, admin_headers):
    await publish(client, admin_headers, name="Public Item")

    for path in ("/categories", "/products"):
        response = await client.get(f"{STOREFRONT}{path}")
        assert response.status_code == 200
