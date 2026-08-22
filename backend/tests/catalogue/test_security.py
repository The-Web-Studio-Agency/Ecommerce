from __future__ import annotations

import pytest

from app.auth.constants import UserRole, UserStatus
from app.auth.security import create_access_token
from tests.conftest import headers_for
from tests.helpers import (
    CATEGORIES,
    IMAGE,
    PRODUCTS,
    VARIANTS,
    make_category,
    make_product,
    make_variant,
)


@pytest.fixture
def unknown_id() -> str:
    return "00000000-0000-0000-0000-000000000000"


async def test_a_tenant_cannot_read_another_tenants_category(
    client, other_client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)

    response = await other_client.get(
        f"{CATEGORIES}/{category['id']}", headers=other_admin_headers
    )

    assert response.status_code == 404


async def test_a_tenant_cannot_update_another_tenants_category(
    client, other_client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)

    response = await other_client.patch(
        f"{CATEGORIES}/{category['id']}",
        json={"name": "Hijacked"},
        headers=other_admin_headers,
    )

    assert response.status_code == 404
    intact = await client.get(f"{CATEGORIES}/{category['id']}", headers=admin_headers)
    assert intact.json()["data"]["name"] == "Dresses"


async def test_a_tenant_cannot_delete_another_tenants_category(
    client, other_client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)

    response = await other_client.delete(
        f"{CATEGORIES}/{category['id']}", headers=other_admin_headers
    )

    assert response.status_code == 404
    assert (
        await client.get(f"{CATEGORIES}/{category['id']}", headers=admin_headers)
    ).status_code == 200


async def test_a_tenant_cannot_read_update_or_delete_another_tenants_product(
    client, other_client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    path = f"{PRODUCTS}/{product['id']}"

    assert (await other_client.get(path, headers=other_admin_headers)).status_code == 404
    assert (
        await other_client.patch(path, json={"name": "Hijacked"}, headers=other_admin_headers)
    ).status_code == 404
    assert (await other_client.delete(path, headers=other_admin_headers)).status_code == 404
    assert (await client.get(path, headers=admin_headers)).status_code == 200


async def test_a_tenant_cannot_read_update_or_delete_another_tenants_variant(
    client, other_client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_variant(client, admin_headers, product["id"])
    path = f"{VARIANTS}/{variant['id']}"

    assert (await other_client.get(path, headers=other_admin_headers)).status_code == 404
    assert (
        await other_client.patch(path, json={"price": "0.01"}, headers=other_admin_headers)
    ).status_code == 404
    assert (await other_client.delete(path, headers=other_admin_headers)).status_code == 404
    assert (await client.get(path, headers=admin_headers)).status_code == 200


async def test_a_list_only_ever_shows_the_callers_own_tenant(
    client, other_client, admin_headers, other_admin_headers
):
    await make_category(client, admin_headers, name="Mine")
    await make_category(other_client, other_admin_headers, name="Theirs")

    response = await client.get(CATEGORIES, headers=admin_headers)

    body = response.json()
    assert body["meta"]["total_items"] == 1
    assert [c["name"] for c in body["data"]] == ["Mine"]


async def test_a_product_cannot_be_created_in_another_tenants_category(
    client, other_client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)

    response = await other_client.post(
        PRODUCTS,
        json={"category_id": category["id"], "name": "Smuggled", "images": [IMAGE]},
        headers=other_admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Category not found"


async def test_a_product_cannot_be_moved_into_another_tenants_category(
    client, other_client, admin_headers, other_admin_headers
):
    victim_category = await make_category(client, admin_headers)
    own_category = await make_category(
        other_client, other_admin_headers, name="Own", slug="own"
    )
    product = await make_product(other_client, other_admin_headers, own_category["id"])

    response = await other_client.patch(
        f"{PRODUCTS}/{product['id']}",
        json={"category_id": victim_category["id"]},
        headers=other_admin_headers,
    )

    assert response.status_code == 404


async def test_a_variant_cannot_be_added_to_another_tenants_product(
    client, other_client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    response = await other_client.post(
        f"{PRODUCTS}/{product['id']}/variants",
        json={"sku": "SMUGGLED-1", "name": "Small", "price": "1.00"},
        headers=other_admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Product not found"


async def test_listing_another_tenants_product_variants_is_a_404(
    client, other_client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    response = await other_client.get(
        f"{PRODUCTS}/{product['id']}/variants", headers=other_admin_headers
    )

    assert response.status_code == 404


async def test_filtering_by_another_tenants_category_is_a_404(
    client, other_client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)

    response = await other_client.get(
        PRODUCTS, params={"category_id": category["id"]}, headers=other_admin_headers
    )

    assert response.status_code == 404


async def test_the_same_category_name_may_exist_in_two_tenants(
    client, other_client, admin_headers, other_admin_headers
):
    await make_category(client, admin_headers)

    response = await other_client.post(
        CATEGORIES, json={"name": "Dresses"}, headers=other_admin_headers
    )

    assert response.status_code == 201


async def test_the_same_sku_may_exist_in_two_tenants(
    client, other_client, admin_headers, other_admin_headers
):
    own = await make_category(client, admin_headers)
    own_product = await make_product(client, admin_headers, own["id"])
    await make_variant(client, admin_headers, own_product["id"], sku="SHARED-1")

    their = await make_category(
        other_client, other_admin_headers, name="Theirs"
    )
    their_product = await make_product(
        other_client, other_admin_headers, their["id"], name="Theirs"
    )

    response = await other_client.post(
        f"{PRODUCTS}/{their_product['id']}/variants",
        json={"sku": "SHARED-1", "name": "Small", "price": "1.00"},
        headers=other_admin_headers,
    )

    assert response.status_code == 201


async def test_a_forged_tenant_claim_does_not_change_scope(
    client, tenant, other_tenant, make_user, admin_headers
):
    await make_category(client, admin_headers)

    intruder = await make_user(
        tenant=other_tenant, email="forger@acme.com", role=UserRole.ADMIN.value
    )
    forged = create_access_token(
        user_id=intruder.id,
        tenant_id=tenant.id,
        role=intruder.role,
    )

    response = await client.get(CATEGORIES, headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


async def test_tenant_id_in_the_body_is_ignored(client, admin_headers, other_tenant):
    response = await client.post(
        CATEGORIES,
        json={"name": "Dresses", "tenant_id": str(other_tenant.id)},
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["tenant_id"] != str(other_tenant.id)


@pytest.fixture
def write_payloads(unknown_id) -> list[tuple[str, str, dict | None]]:
    return [
        ("post", CATEGORIES, {"name": "X"}),
        ("patch", f"{CATEGORIES}/{unknown_id}", {"name": "X"}),
        ("delete", f"{CATEGORIES}/{unknown_id}", None),
        ("post", PRODUCTS, {"category_id": unknown_id, "name": "X", "images": [IMAGE]}),
        ("patch", f"{PRODUCTS}/{unknown_id}", {"name": "X"}),
        ("delete", f"{PRODUCTS}/{unknown_id}", None),
        ("post", f"{PRODUCTS}/{unknown_id}/variants", {"sku": "X1", "name": "X", "price": "1.00"}),
        ("patch", f"{VARIANTS}/{unknown_id}", {"price": "1.00"}),
        ("delete", f"{VARIANTS}/{unknown_id}", None),
    ]


async def test_staff_may_read_the_catalogue(client, admin_headers, staff_headers):
    await make_category(client, admin_headers)

    assert (await client.get(CATEGORIES, headers=staff_headers)).status_code == 200
    assert (await client.get(PRODUCTS, headers=staff_headers)).status_code == 200


async def test_staff_may_not_write_to_the_catalogue(client, staff_headers, write_payloads):
    for method, path, payload in write_payloads:
        response = await client.request(method, path, json=payload, headers=staff_headers)
        assert response.status_code == 403, f"{method.upper()} {path} -> {response.status_code}"
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"


async def test_a_customer_may_not_touch_the_catalogue(
    client, customer_headers, write_payloads
):
    assert (await client.get(CATEGORIES, headers=customer_headers)).status_code == 403

    for method, path, payload in write_payloads:
        response = await client.request(method, path, json=payload, headers=customer_headers)
        assert response.status_code == 403, f"{method.upper()} {path} -> {response.status_code}"


async def test_a_forged_role_claim_grants_nothing(client, tenant, make_user):
    customer = await make_user(tenant=tenant, phone="+919000222333")
    forged = create_access_token(
        user_id=customer.id,
        tenant_id=customer.tenant_id,
        role=UserRole.ADMIN.value,
    )

    response = await client.post(
        CATEGORIES,
        json={"name": "Escalated"},
        headers={"Authorization": f"Bearer {forged}"},
    )

    assert response.status_code == 403


async def test_a_deactivated_admin_loses_catalogue_access(client, session, tenant, make_user):
    admin = await make_user(tenant=tenant, email="gone@zeen.com", role=UserRole.ADMIN.value)
    headers = headers_for(admin)
    assert (await client.get(CATEGORIES, headers=headers)).status_code == 200

    admin.status = UserStatus.INACTIVE.value
    await session.commit()

    assert (await client.get(CATEGORIES, headers=headers)).status_code == 401


async def test_an_anonymous_caller_is_rejected(client, tenant):
    assert (await client.get(CATEGORIES)).status_code == 401
    assert (
        await client.post(CATEGORIES, json={"name": "X"})
    ).status_code == 401
