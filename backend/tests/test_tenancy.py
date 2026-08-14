"""Tenant isolation: the boundary between two tenants sharing one database."""

from __future__ import annotations

from sqlalchemy import select

from app.users.models import User
from app.users.repository import UserRepository
from tests.conftest import USER_PASSWORD, access_token_for, login


async def test_same_email_in_two_tenants_stays_separate(client, tenant, other_tenant, make_user):
    """One address may exist in several tenants and they must not be confused."""
    shared = "shared@example.com"
    zeen_user = await make_user(tenant=tenant, email=shared, password=USER_PASSWORD)
    acme_user = await make_user(tenant=other_tenant, email=shared, password="a-different-one")

    assert zeen_user.id != acme_user.id

    zeen_login = await login(client, slug="zeen", email=shared, password=USER_PASSWORD)
    assert zeen_login.status_code == 200
    assert zeen_login.json()["data"]["user"]["id"] == str(zeen_user.id)

    # The other tenant's password must not authenticate against this tenant.
    crossed = await login(client, slug="zeen", email=shared, password="a-different-one")
    assert crossed.status_code == 401


async def test_login_is_scoped_to_the_requested_tenant(client, tenant, other_tenant, make_user):
    """An account in one tenant cannot be used to log into another."""
    await make_user(tenant=tenant, email="only-zeen@example.com")

    response = await login(
        client, slug="acme", email="only-zeen@example.com", password=USER_PASSWORD
    )

    assert response.status_code == 401


async def test_me_reports_the_callers_own_tenant(client, tenant, other_tenant, user):
    token = await access_token_for(client, slug="zeen", email=user.email, password=USER_PASSWORD)

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.json()["data"]["tenant_id"] == str(tenant.id)


async def test_header_cannot_override_the_authenticated_tenant(
    client, tenant, other_tenant, user
):
    """An authenticated caller's scope comes from their user row, never a header."""
    token = await access_token_for(client, slug="zeen", email=user.email, password=USER_PASSWORD)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Slug": "acme"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["tenant_id"] == str(tenant.id)


async def test_lookup_by_email_requires_the_right_tenant(
    session, tenant, other_tenant, make_user
):
    """Every user query is keyed on (tenant, email), never email alone."""
    await make_user(tenant=other_tenant, email="theirs@example.com")
    users = UserRepository(session)

    assert await users.get_by_tenant_and_email(
        tenant_id=other_tenant.id, email="theirs@example.com"
    ) is not None
    assert await users.get_by_tenant_and_email(
        tenant_id=tenant.id, email="theirs@example.com"
    ) is None


async def test_registration_binds_the_user_to_the_named_tenant(client, tenant, other_tenant):
    response = await client.post(
        "/api/v1/auth/register",
        json={"tenant_slug": "acme", "email": "new@example.com", "password": "a-good-password"},
    )

    assert response.status_code == 201
    assert response.json()["data"]["tenant_id"] == str(other_tenant.id)


async def test_deactivating_one_tenant_does_not_affect_another(
    client, session, tenant, other_tenant, make_user
):
    await make_user(tenant=other_tenant, email="acme-user@example.com")

    tenant.is_active = False
    await session.commit()

    blocked = await login(client, slug="zeen", email="user@zeen.com", password=USER_PASSWORD)
    allowed = await login(
        client, slug="acme", email="acme-user@example.com", password=USER_PASSWORD
    )

    assert blocked.status_code == 401
    assert allowed.status_code == 200


async def test_users_from_both_tenants_coexist(session, tenant, other_tenant, make_user):
    """Sanity check: isolation comes from the query scope, not from empty tables."""
    await make_user(tenant=tenant, email="a@example.com")
    await make_user(tenant=other_tenant, email="c@example.com")

    all_users = (await session.execute(select(User))).scalars().all()

    assert len(all_users) == 2
