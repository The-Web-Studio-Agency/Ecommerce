from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.catalogue.models import ProductImage
from app.catalogue.service import ProductImageService
from app.core.exceptions import ConflictError
from tests.test_catalogue import IMAGE, PRODUCTS, make_category, make_product

IMAGES = "/api/v1/catalogue/images"


def product_images(product_id) -> str:
    return f"{PRODUCTS}/{product_id}/images"


async def make_product_with_images(client, headers, count=3) -> tuple[dict, list[dict]]:
    category = await make_category(client, headers)
    product = await make_product(
        client,
        headers,
        category["id"],
        images=[
            {"url": f"https://cdn.example.com/{index}.jpg", "sort_order": index}
            for index in range(count)
        ],
    )
    listed = await client.get(product_images(product["id"]), headers=headers)
    return product, listed.json()["data"]


async def test_a_product_can_hold_several_images_in_sort_order(client, admin_headers):
    _product, images = await make_product_with_images(client, admin_headers, count=3)

    assert len(images) == 3
    assert [image["sort_order"] for image in images] == [0, 1, 2]


async def test_the_last_image_cannot_be_deleted(client, admin_headers):
    product, images = await make_product_with_images(client, admin_headers, count=2)

    first = await client.delete(f"{IMAGES}/{images[0]['id']}", headers=admin_headers)
    assert first.status_code == 204

    last = await client.delete(f"{IMAGES}/{images[1]['id']}", headers=admin_headers)
    assert last.status_code == 409
    assert last.json()["message"] == "A product must have at least one image"

    remaining = await client.get(product_images(product["id"]), headers=admin_headers)
    assert len(remaining.json()["data"]) == 1


async def test_deleting_the_primary_image_promotes_another(client, admin_headers):
    product, images = await make_product_with_images(client, admin_headers, count=3)
    primary = next(image for image in images if image["is_primary"])

    assert (
        await client.delete(f"{IMAGES}/{primary['id']}", headers=admin_headers)
    ).status_code == 204

    remaining = (
        await client.get(product_images(product["id"]), headers=admin_headers)
    ).json()["data"]

    assert sum(1 for image in remaining if image["is_primary"]) == 1


async def test_another_tenants_image_cannot_be_read_or_deleted(
    client, other_client, admin_headers, other_admin_headers
):
    _product, images = await make_product_with_images(client, admin_headers, count=2)
    victim = images[0]["id"]

    assert (
        await other_client.patch(
            f"{IMAGES}/{victim}", json={"alt_text": "stolen"}, headers=other_admin_headers
        )
    ).status_code == 404

    assert (
        await other_client.delete(f"{IMAGES}/{victim}", headers=other_admin_headers)
    ).status_code == 404

    assert (
        await other_client.post(
            f"{IMAGES}/{victim}/primary", headers=other_admin_headers
        )
    ).status_code == 404


async def test_setting_a_primary_demotes_the_previous_one(client, admin_headers):
    product, images = await make_product_with_images(client, admin_headers, count=3)

    response = await client.post(
        f"{IMAGES}/{images[2]['id']}/primary", headers=admin_headers
    )
    assert response.status_code == 200

    listed = (
        await client.get(product_images(product["id"]), headers=admin_headers)
    ).json()["data"]

    primaries = [image["id"] for image in listed if image["is_primary"]]
    assert primaries == [images[2]["id"]]


async def test_images_can_be_reordered(client, admin_headers):
    product, images = await make_product_with_images(client, admin_headers, count=3)

    response = await client.put(
        f"{product_images(product['id'])}/order",
        json={
            "images": [
                {"id": images[2]["id"], "sort_order": 0},
                {"id": images[1]["id"], "sort_order": 1},
                {"id": images[0]["id"], "sort_order": 2},
            ]
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert [image["id"] for image in response.json()["data"]] == [
        images[2]["id"],
        images[1]["id"],
        images[0]["id"],
    ]


async def test_reordering_rejects_an_image_from_another_product(client, admin_headers):
    product_a, images_a = await make_product_with_images(client, admin_headers, count=2)
    _product_b, images_b = await make_product_with_images(client, admin_headers, count=2)

    response = await client.put(
        f"{product_images(product_a['id'])}/order",
        json={"images": [{"id": images_b[0]["id"], "sort_order": 0}]},
        headers=admin_headers,
    )

    assert response.status_code == 404


async def test_alt_text_can_be_updated(client, admin_headers):
    _product, images = await make_product_with_images(client, admin_headers, count=2)

    response = await client.patch(
        f"{IMAGES}/{images[0]['id']}",
        json={"alt_text": "  Model wearing the dress  "},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["alt_text"] == "Model wearing the dress"


async def test_concurrent_primary_updates_leave_exactly_one_primary(
    engine, session, tenant, client, admin_headers
):
    """
    The partial unique index is the thing under test.

    Several sessions race to claim primary; the database must let at most one
    win, and the losers must surface as a clean ConflictError rather than a
    second primary row.
    """
    product, images = await make_product_with_images(client, admin_headers, count=4)
    product_id = UUID(product["id"])

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def claim(image_id: str) -> str:
        async with factory() as own_session:
            try:
                await ProductImageService(own_session, tenant.id).set_primary(
                    UUID(image_id)
                )
                return "won"
            except ConflictError:
                return "lost"

    results = await asyncio.gather(*[claim(image["id"]) for image in images])
    assert "won" in results

    primaries = await session.scalar(
        select(func.count())
        .select_from(ProductImage)
        .where(
            ProductImage.tenant_id == tenant.id,
            ProductImage.product_id == product_id,
            ProductImage.is_primary.is_(True),
        )
    )
    assert primaries == 1, results


async def test_concurrent_deletes_cannot_empty_a_product(
    engine, session, tenant, client, admin_headers
):
    """Two deletes racing on a two-image product must leave one behind."""
    product, images = await make_product_with_images(client, admin_headers, count=2)
    product_id = UUID(product["id"])

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def remove(image_id: str) -> str:
        async with factory() as own_session:
            try:
                await ProductImageService(own_session, tenant.id).delete(UUID(image_id))
                return "deleted"
            except ConflictError:
                return "refused"

    results = await asyncio.gather(*[remove(image["id"]) for image in images])

    remaining = await session.scalar(
        select(func.count())
        .select_from(ProductImage)
        .where(
            ProductImage.tenant_id == tenant.id,
            ProductImage.product_id == product_id,
        )
    )
    assert remaining >= 1, results
    assert results.count("deleted") == 1, results


async def test_an_image_cannot_be_added_to_an_archived_product(client, admin_headers):
    product, _images = await make_product_with_images(client, admin_headers, count=2)

    await client.delete(f"{PRODUCTS}/{product['id']}", headers=admin_headers)

    response = await client.post(
        product_images(product["id"]), json=IMAGE, headers=admin_headers
    )

    assert response.status_code == 409
