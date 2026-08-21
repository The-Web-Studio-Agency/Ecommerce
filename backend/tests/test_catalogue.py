from __future__ import annotations

import pytest

CATEGORIES = "/api/v1/catalogue/categories"
PRODUCTS = "/api/v1/catalogue/products"
VARIANTS = "/api/v1/catalogue/variants"


IMAGE = {"url": "https://cdn.example.com/dress.jpg", "alt_text": "Front view"}


async def make_category(client, headers, **overrides) -> dict:
    payload = {"name": "Dresses", "description": "Womenswear"}
    payload.update(overrides)
    response = await client.post(CATEGORIES, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def make_product(client, headers, category_id, **overrides) -> dict:
    payload = {"category_id": category_id, "name": "Summer Dress", "images": [IMAGE]}
    payload.update(overrides)
    response = await client.post(PRODUCTS, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def make_variant(client, headers, product_id, **overrides) -> dict:
    payload = {"sku": "DRESS-S-BLK", "name": "Small / Black", "price": "49.99"}
    payload.update(overrides)
    response = await client.post(
        f"{PRODUCTS}/{product_id}/variants", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def test_create_and_retrieve_a_category(client, admin_headers):
    created = await make_category(client, admin_headers)

    assert created["name"] == "Dresses"
    assert created["is_active"] is True

    response = await client.get(f"{CATEGORIES}/{created['id']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == created["id"]


async def test_update_a_category(client, admin_headers):
    created = await make_category(client, admin_headers)

    response = await client.patch(
        f"{CATEGORIES}/{created['id']}",
        json={"name": "Evening Dresses", "is_active": False},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["name"] == "Evening Dresses"
    assert body["is_active"] is False


async def test_delete_a_category(client, admin_headers):
    created = await make_category(client, admin_headers)

    assert (
        await client.delete(f"{CATEGORIES}/{created['id']}", headers=admin_headers)
    ).status_code == 204
    assert (
        await client.get(f"{CATEGORIES}/{created['id']}", headers=admin_headers)
    ).status_code == 404


async def test_a_category_with_products_cannot_be_deleted(client, admin_headers):
    category = await make_category(client, admin_headers)
    await make_product(client, admin_headers, category["id"])

    response = await client.delete(f"{CATEGORIES}/{category['id']}", headers=admin_headers)

    assert response.status_code == 409
    assert "products" in response.json()["message"].lower()


@pytest.mark.parametrize("payload", [{"name": ""}, {"name": "   "}])
async def test_invalid_category_updates_are_rejected(client, admin_headers, payload):
    created = await make_category(client, admin_headers)

    response = await client.patch(
        f"{CATEGORIES}/{created['id']}", json=payload, headers=admin_headers
    )

    assert response.status_code == 422


async def test_an_empty_patch_changes_nothing(client, admin_headers):
    created = await make_category(client, admin_headers)

    response = await client.patch(
        f"{CATEGORIES}/{created['id']}", json={}, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["data"] == created


async def test_unknown_category_is_a_404(client, admin_headers):
    unknown = "00000000-0000-0000-0000-000000000000"

    response = await client.get(f"{CATEGORIES}/{unknown}", headers=admin_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 200},
        {},
    ],
)
async def test_invalid_category_payloads_are_rejected(client, admin_headers, payload):
    response = await client.post(CATEGORIES, json=payload, headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_create_and_retrieve_a_product(client, admin_headers):
    category = await make_category(client, admin_headers)

    created = await make_product(client, admin_headers, category["id"])

    assert created["category_id"] == category["id"]
    assert created["status"] == "DRAFT"

    response = await client.get(f"{PRODUCTS}/{created['id']}", headers=admin_headers)
    assert response.status_code == 200


async def test_a_product_needs_an_existing_category(client, admin_headers):
    response = await client.post(
        PRODUCTS,
        json={
            "category_id": "00000000-0000-0000-0000-000000000000",
            "name": "Orphan",
            "images": [IMAGE],
        },
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Category not found"


async def test_update_a_product_status_and_category(client, admin_headers):
    category = await make_category(client, admin_headers)
    other = await make_category(client, admin_headers, name="Skirts")
    product = await make_product(client, admin_headers, category["id"])

    response = await client.patch(
        f"{PRODUCTS}/{product['id']}",
        json={"status": "ACTIVE", "category_id": other["id"]},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "ACTIVE"
    assert body["category_id"] == other["id"]


async def test_a_product_cannot_be_moved_to_an_unknown_category(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    response = await client.patch(
        f"{PRODUCTS}/{product['id']}",
        json={"category_id": "00000000-0000-0000-0000-000000000000"},
        headers=admin_headers,
    )

    assert response.status_code == 404


async def test_an_invalid_status_is_rejected(client, admin_headers):
    category = await make_category(client, admin_headers)

    response = await client.post(
        PRODUCTS,
        json={
            "category_id": category["id"],
            "name": "Bad",
            "images": [IMAGE],
            "status": "ON_FIRE",
        },
        headers=admin_headers,
    )

    assert response.status_code == 422


async def test_products_can_be_filtered_by_category(client, admin_headers):
    first = await make_category(client, admin_headers)
    second = await make_category(client, admin_headers, name="Skirts")
    await make_product(client, admin_headers, first["id"])
    await make_product(client, admin_headers, second["id"], name="Midi")

    response = await client.get(
        PRODUCTS, params={"category_id": second["id"]}, headers=admin_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total_items"] == 1
    assert body["data"][0]["name"] == "Midi"


async def test_deleting_a_product_archives_it_and_its_variants(client, admin_headers):
    """
    Products and variants are archived rather than dropped, so order history
    keeps resolving. Staff still see the rows; the storefront must not.
    """
    category = await make_category(client, admin_headers)
    product = await make_product(
        client, admin_headers, category["id"], status="ACTIVE"
    )
    variant = await make_variant(
        client, admin_headers, product["id"], status="ACTIVE"
    )

    assert (
        await client.delete(f"{PRODUCTS}/{product['id']}", headers=admin_headers)
    ).status_code == 204

    still_there = await client.get(f"{VARIANTS}/{variant['id']}", headers=admin_headers)
    assert still_there.status_code == 200
    assert still_there.json()["data"]["status"] == "ARCHIVED"

    hidden = await client.get(f"/api/v1/storefront/variants/{variant['id']}")
    assert hidden.status_code == 404


async def test_a_product_cannot_be_created_without_an_image(client, admin_headers):
    category = await make_category(client, admin_headers)

    missing = await client.post(
        PRODUCTS,
        json={"category_id": category["id"], "name": "No Artwork"},
        headers=admin_headers,
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "VALIDATION_ERROR"

    empty = await client.post(
        PRODUCTS,
        json={"category_id": category["id"], "name": "No Artwork", "images": []},
        headers=admin_headers,
    )
    assert empty.status_code == 422


async def test_product_images_are_stored_with_the_product(client, admin_headers):
    category = await make_category(client, admin_headers)

    created = await make_product(
        client,
        admin_headers,
        category["id"],
        images=[
            {"url": "https://cdn.example.com/a.jpg", "sort_order": 0},
            {"url": "https://cdn.example.com/b.jpg", "sort_order": 1},
        ],
    )

    assert [image["url"] for image in created["images"]] == [
        "https://cdn.example.com/a.jpg",
        "https://cdn.example.com/b.jpg",
    ]
    # Nobody nominated a primary, so the first image becomes one.
    assert [image["is_primary"] for image in created["images"]] == [True, False]


async def test_only_one_image_may_be_marked_primary(client, admin_headers):
    category = await make_category(client, admin_headers)

    response = await client.post(
        PRODUCTS,
        json={
            "category_id": category["id"],
            "name": "Two Primaries",
            "images": [
                {"url": "https://cdn.example.com/a.jpg", "is_primary": True},
                {"url": "https://cdn.example.com/b.jpg", "is_primary": True},
            ],
        },
        headers=admin_headers,
    )

    assert response.status_code == 422


async def test_create_and_retrieve_a_variant(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    created = await make_variant(client, admin_headers, product["id"])

    assert created["product_id"] == product["id"]
    assert created["sku"] == "DRESS-S-BLK"
    assert created["price"] == "49.99"

    response = await client.get(f"{VARIANTS}/{created['id']}", headers=admin_headers)
    assert response.status_code == 200


async def test_a_sku_is_uppercased_before_it_is_stored(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    created = await make_variant(client, admin_headers, product["id"], sku="dress-m-blk")

    assert created["sku"] == "DRESS-M-BLK"


async def test_sku_uniqueness_ignores_case(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    await make_variant(client, admin_headers, product["id"], sku="DRESS-S-BLK")

    response = await client.post(
        f"{PRODUCTS}/{product['id']}/variants",
        json={"sku": "dress-s-blk", "name": "Small / Black", "price": "10.00"},
        headers=admin_headers,
    )

    assert response.status_code == 409


async def test_a_sku_is_unique_across_the_whole_tenant(client, admin_headers):
    category = await make_category(client, admin_headers)
    first = await make_product(client, admin_headers, category["id"])
    second = await make_product(client, admin_headers, category["id"], name="Other")
    await make_variant(client, admin_headers, first["id"])

    response = await client.post(
        f"{PRODUCTS}/{second['id']}/variants",
        json={"sku": "DRESS-S-BLK", "name": "Small / Black", "price": "10.00"},
        headers=admin_headers,
    )

    assert response.status_code == 409


async def test_a_variant_needs_an_existing_product(client, admin_headers):
    response = await client.post(
        f"{PRODUCTS}/00000000-0000-0000-0000-000000000000/variants",
        json={"sku": "X-1", "name": "One", "price": "1.00"},
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Product not found"


@pytest.mark.parametrize("price", ["-1.00", "-0.01"])
async def test_a_negative_price_is_rejected(client, admin_headers, price):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    response = await client.post(
        f"{PRODUCTS}/{product['id']}/variants",
        json={"sku": "NEG-1", "name": "Negative", "price": price},
        headers=admin_headers,
    )

    assert response.status_code == 422


async def test_a_price_may_be_zero(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    created = await make_variant(client, admin_headers, product["id"], price="0.00")

    assert created["price"] == "0.00"


async def test_too_many_decimal_places_is_rejected(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    response = await client.post(
        f"{PRODUCTS}/{product['id']}/variants",
        json={"sku": "FRAC-1", "name": "Fractional", "price": "10.001"},
        headers=admin_headers,
    )

    assert response.status_code == 422


async def test_update_a_variant(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_variant(client, admin_headers, product["id"])

    response = await client.patch(
        f"{VARIANTS}/{variant['id']}",
        json={"price": "59.50", "status": "ACTIVE"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["price"] == "59.50"
    assert body["status"] == "ACTIVE"
    assert body["sku"] == "DRESS-S-BLK"


async def test_delete_a_variant_archives_it(client, admin_headers):
    """Variants are archived, not dropped -- carts and orders reference them."""
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_variant(
        client, admin_headers, product["id"], status="ACTIVE"
    )

    assert (
        await client.delete(f"{VARIANTS}/{variant['id']}", headers=admin_headers)
    ).status_code == 204

    archived = await client.get(f"{VARIANTS}/{variant['id']}", headers=admin_headers)
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "ARCHIVED"

    assert (
        await client.get(f"/api/v1/storefront/variants/{variant['id']}")
    ).status_code == 404


async def test_categories_are_paginated(client, admin_headers):
    for index in range(3):
        await make_category(client, admin_headers, name=f"C{index}")

    response = await client.get(
        CATEGORIES, params={"page": 2, "page_size": 2}, headers=admin_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {
        "page": 2,
        "page_size": 2,
        "total_items": 3,
        "total_pages": 2,
    }
    assert len(body["data"]) == 1


async def test_products_are_paginated(client, admin_headers):
    category = await make_category(client, admin_headers)
    for index in range(3):
        await make_product(client, admin_headers, category["id"], name=f"P{index}")

    response = await client.get(
        PRODUCTS, params={"page": 1, "page_size": 2}, headers=admin_headers
    )

    assert response.json()["meta"]["total_items"] == 3
    assert len(response.json()["data"]) == 2


async def test_variants_are_paginated(client, admin_headers):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    for index in range(3):
        await make_variant(client, admin_headers, product["id"], sku=f"SKU-{index}")

    response = await client.get(
        f"{PRODUCTS}/{product['id']}/variants",
        params={"page": 1, "page_size": 2},
        headers=admin_headers,
    )

    assert response.json()["meta"]["total_items"] == 3
    assert len(response.json()["data"]) == 2


async def test_the_page_size_ceiling_is_enforced(client, admin_headers):
    response = await client.get(CATEGORIES, params={"page_size": 1000}, headers=admin_headers)

    assert response.status_code == 422


async def test_a_filtered_total_reflects_the_filter(client, admin_headers):
    first = await make_category(client, admin_headers)
    second = await make_category(client, admin_headers, name="Skirts")
    await make_product(client, admin_headers, first["id"])
    await make_product(client, admin_headers, second["id"], name="Midi")

    response = await client.get(
        PRODUCTS, params={"category_id": first["id"]}, headers=admin_headers
    )

    assert response.json()["meta"]["total_items"] == 1
