"""Catalogue tenant isolation and authorization.

Catalogue is the first module built on `TenantScopedRepository`, so these tests
are the proof that the boundary actually holds for a real resource - not just
that reads are filtered, but that an id belonging to another tenant cannot be
read, written, deleted, or attached to.

Every case goes over HTTP. A service called directly would prove the service;
only a request proves the chain the client actually reaches.
"""

from __future__ import annotations

import pytest

from app.auth.constants import UserRole
from app.auth.security import create_access_token
from tests.conftest import headers_for
from tests.test_catalogue import (
    CATEGORIES,
    PRODUCTS,
    VARIANTS,
    make_category,
    make_product,
    make_variant,
)


@pytest.fixture
def unknown_id() -> str:
    return "00000000-0000-0000-0000-000000000000"


# ------------------------------------------------------------ isolation


async def test_a_tenant_cannot_read_another_tenants_category(
    client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)

    response = await client.get(f"{CATEGORIES}/{category['id']}", headers=other_admin_headers)

    # 404, not 403: another tenant's row is indistinguishable from a missing
    # one, so ids cannot be probed for existence across tenants.
    assert response.status_code == 404


async def test_a_tenant_cannot_update_another_tenants_category(
    client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)

    response = await client.patch(
        f"{CATEGORIES}/{category['id']}", json={"name": "Hijacked"}, headers=other_admin_headers
    )

    assert response.status_code == 404
    # And the original is untouched.
    intact = await client.get(f"{CATEGORIES}/{category['id']}", headers=admin_headers)
    assert intact.json()["data"]["name"] == "Dresses"


async def test_a_tenant_cannot_delete_another_tenants_category(
    client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)

    response = await client.delete(f"{CATEGORIES}/{category['id']}", headers=other_admin_headers)

    assert response.status_code == 404
    assert (
        await client.get(f"{CATEGORIES}/{category['id']}", headers=admin_headers)
    ).status_code == 200


async def test_a_tenant_cannot_read_update_or_delete_another_tenants_product(
    client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    path = f"{PRODUCTS}/{product['id']}"

    assert (await client.get(path, headers=other_admin_headers)).status_code == 404
    assert (
        await client.patch(path, json={"name": "Hijacked"}, headers=other_admin_headers)
    ).status_code == 404
    assert (await client.delete(path, headers=other_admin_headers)).status_code == 404
    assert (await client.get(path, headers=admin_headers)).status_code == 200


async def test_a_tenant_cannot_read_update_or_delete_another_tenants_variant(
    client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])
    variant = await make_variant(client, admin_headers, product["id"])
    path = f"{VARIANTS}/{variant['id']}"

    assert (await client.get(path, headers=other_admin_headers)).status_code == 404
    assert (
        await client.patch(path, json={"price": "0.01"}, headers=other_admin_headers)
    ).status_code == 404
    assert (await client.delete(path, headers=other_admin_headers)).status_code == 404
    assert (await client.get(path, headers=admin_headers)).status_code == 200


async def test_a_list_only_ever_shows_the_callers_own_tenant(
    client, admin_headers, other_admin_headers
):
    await make_category(client, admin_headers, name="Mine", slug="mine")
    await make_category(client, other_admin_headers, name="Theirs", slug="theirs")

    response = await client.get(CATEGORIES, headers=admin_headers)

    body = response.json()
    assert body["meta"]["total_items"] == 1
    assert [c["slug"] for c in body["data"]] == ["mine"]


# ------------------------------------------------- indirect / cross references


async def test_a_product_cannot_be_created_in_another_tenants_category(
    client, admin_headers, other_admin_headers
):
    """The classic multi-tenant hole: a valid id from the wrong tenant."""
    category = await make_category(client, admin_headers)

    response = await client.post(
        PRODUCTS,
        json={"category_id": category["id"], "name": "Smuggled", "slug": "smuggled"},
        headers=other_admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Category not found"


async def test_a_product_cannot_be_moved_into_another_tenants_category(
    client, admin_headers, other_admin_headers
):
    victim_category = await make_category(client, admin_headers)
    own_category = await make_category(client, other_admin_headers, name="Own", slug="own")
    product = await make_product(client, other_admin_headers, own_category["id"])

    response = await client.patch(
        f"{PRODUCTS}/{product['id']}",
        json={"category_id": victim_category["id"]},
        headers=other_admin_headers,
    )

    assert response.status_code == 404


async def test_a_variant_cannot_be_added_to_another_tenants_product(
    client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    response = await client.post(
        f"{PRODUCTS}/{product['id']}/variants",
        json={"sku": "SMUGGLED-1", "name": "Small", "price": "1.00"},
        headers=other_admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Product not found"


async def test_listing_another_tenants_product_variants_is_a_404(
    client, admin_headers, other_admin_headers
):
    category = await make_category(client, admin_headers)
    product = await make_product(client, admin_headers, category["id"])

    response = await client.get(
        f"{PRODUCTS}/{product['id']}/variants", headers=other_admin_headers
    )

    assert response.status_code == 404


async def test_filtering_by_another_tenants_category_is_a_404(
    client, admin_headers, other_admin_headers
):
    """An unknown filter must not silently return an empty page."""
    category = await make_category(client, admin_headers)

    response = await client.get(
        PRODUCTS, params={"category_id": category["id"]}, headers=other_admin_headers
    )

    assert response.status_code == 404


async def test_the_same_slug_may_exist_in_two_tenants(
    client, admin_headers, other_admin_headers
):
    """Isolation cuts both ways: uniqueness is per tenant, not global."""
    await make_category(client, admin_headers)

    response = await client.post(
        CATEGORIES, json={"name": "Dresses", "slug": "dresses"}, headers=other_admin_headers
    )

    assert response.status_code == 201


async def test_the_same_sku_may_exist_in_two_tenants(
    client, admin_headers, other_admin_headers
):
    own = await make_category(client, admin_headers)
    own_product = await make_product(client, admin_headers, own["id"])
    await make_variant(client, admin_headers, own_product["id"], sku="SHARED-1")

    their = await make_category(client, other_admin_headers, name="Theirs", slug="theirs")
    their_product = await make_product(
        client, other_admin_headers, their["id"], name="Theirs", slug="theirs-product"
    )

    response = await client.post(
        f"{PRODUCTS}/{their_product['id']}/variants",
        json={"sku": "SHARED-1", "name": "Small", "price": "1.00"},
        headers=other_admin_headers,
    )

    assert response.status_code == 201


# ------------------------------------------------------------- forged input


async def test_a_forged_tenant_claim_does_not_change_scope(
    client, tenant, other_tenant, make_user, admin_headers
):
    """The JWT's `tid` is a claim; the user row is the authority."""
    category = await make_category(client, admin_headers)

    intruder = await make_user(
        tenant=other_tenant, email="forger@acme.com", role=UserRole.TENANT_ADMIN.value
    )
    forged = create_access_token(
        subject=str(intruder.id),
        role=intruder.role,
        tenant_id=str(tenant.id),  # lie: claim the victim's tenant
    )

    response = await client.get(
        f"{CATEGORIES}/{category['id']}", headers={"Authorization": f"Bearer {forged}"}
    )

    assert response.status_code == 404


async def test_tenant_id_in_the_body_is_ignored(client, admin_headers, other_tenant):
    """There is no tenant field to set; an extra one is dropped, not honoured."""
    response = await client.post(
        CATEGORIES,
        json={"name": "Dresses", "slug": "dresses", "tenant_id": str(other_tenant.id)},
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["tenant_id"] != str(other_tenant.id)


# ------------------------------------------------------------------- RBAC


@pytest.fixture
def write_payloads(unknown_id) -> list[tuple[str, str, dict | None]]:
    """Every catalogue write, for permission checks."""
    return [
        ("post", CATEGORIES, {"name": "X", "slug": "x"}),
        ("patch", f"{CATEGORIES}/{unknown_id}", {"name": "X"}),
        ("delete", f"{CATEGORIES}/{unknown_id}", None),
        ("post", PRODUCTS, {"category_id": unknown_id, "name": "X", "slug": "x"}),
        ("patch", f"{PRODUCTS}/{unknown_id}", {"name": "X"}),
        ("delete", f"{PRODUCTS}/{unknown_id}", None),
        ("post", f"{PRODUCTS}/{unknown_id}/variants", {"sku": "X1", "name": "X", "price": "1.00"}),
        ("patch", f"{VARIANTS}/{unknown_id}", {"price": "1.00"}),
        ("delete", f"{VARIANTS}/{unknown_id}", None),
    ]


async def _staff_headers(client, tenant, make_user) -> dict[str, str]:
    await make_user(tenant=tenant, email="staff@zeen.com", role=UserRole.STAFF.value)
    return await headers_for(client, slug=tenant.slug, email="staff@zeen.com")


async def _customer_headers(client, tenant, make_user) -> dict[str, str]:
    await make_user(tenant=tenant, email="shopper@zeen.com", role=UserRole.CUSTOMER.value)
    return await headers_for(client, slug=tenant.slug, email="shopper@zeen.com")


async def test_staff_may_read_the_catalogue(client, tenant, make_user, admin_headers):
    await make_category(client, admin_headers)
    headers = await _staff_headers(client, tenant, make_user)

    assert (await client.get(CATEGORIES, headers=headers)).status_code == 200
    assert (await client.get(PRODUCTS, headers=headers)).status_code == 200


async def test_staff_may_not_write_to_the_catalogue(
    client, tenant, make_user, write_payloads
):
    """Staff run the shop day to day; they do not restructure the catalogue."""
    headers = await _staff_headers(client, tenant, make_user)

    for method, path, payload in write_payloads:
        response = await client.request(method, path, json=payload, headers=headers)
        assert response.status_code == 403, f"{method.upper()} {path} -> {response.status_code}"
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"


async def test_a_customer_may_not_touch_the_catalogue(
    client, tenant, make_user, write_payloads
):
    headers = await _customer_headers(client, tenant, make_user)

    assert (await client.get(CATEGORIES, headers=headers)).status_code == 403

    for method, path, payload in write_payloads:
        response = await client.request(method, path, json=payload, headers=headers)
        assert response.status_code == 403, f"{method.upper()} {path} -> {response.status_code}"


async def test_a_forged_role_claim_grants_nothing(client, tenant, make_user):
    """Permissions come from the database row, not the token's `role`."""
    customer = await make_user(
        tenant=tenant, email="climber@zeen.com", role=UserRole.CUSTOMER.value
    )
    forged = create_access_token(
        subject=str(customer.id),
        role=UserRole.TENANT_ADMIN.value,  # lie
        tenant_id=str(customer.tenant_id),
    )

    response = await client.post(
        CATEGORIES,
        json={"name": "Escalated", "slug": "escalated"},
        headers={"Authorization": f"Bearer {forged}"},
    )

    assert response.status_code == 403


async def test_a_deactivated_admin_loses_catalogue_access(
    client, session, tenant, make_user
):
    """A live token is not a free pass: user state is re-checked per request."""
    user = await make_user(
        tenant=tenant, email="gone@zeen.com", role=UserRole.TENANT_ADMIN.value
    )
    headers = await headers_for(client, slug=tenant.slug, email="gone@zeen.com")
    assert (await client.get(CATEGORIES, headers=headers)).status_code == 200

    user.is_active = False
    await session.commit()

    assert (await client.get(CATEGORIES, headers=headers)).status_code == 401


async def test_an_anonymous_caller_is_rejected(client):
    assert (await client.get(CATEGORIES)).status_code == 401
    assert (
        await client.post(CATEGORIES, json={"name": "X", "slug": "x"})
    ).status_code == 401
