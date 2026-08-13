"""Tenant isolation: the boundary between two tenants sharing one database."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.exceptions import NotFoundError, TenantContextError
from app.core.repository import TenantScopedRepository
from app.core.tenant_context import TenantContext
from app.tenants.dependencies import get_public_tenant_context
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


# ------------------------------------------------- public tenant resolution


async def test_public_tenant_context_resolves_from_header(session, tenant):
    context = await get_public_tenant_context(x_tenant_slug="ZEEN", session=session)

    assert context.tenant_id == tenant.id
    assert context.slug == "zeen"


async def test_public_tenant_context_requires_an_identifier(session):
    with pytest.raises(TenantContextError):
        await get_public_tenant_context(x_tenant_slug=None, session=session)


async def test_public_tenant_context_rejects_inactive_tenant(session, tenant):
    tenant.is_active = False
    await session.commit()

    with pytest.raises(NotFoundError):
        await get_public_tenant_context(x_tenant_slug="zeen", session=session)


# ------------------------------------------------ tenant-scoped repositories


class _UserScopedRepository(TenantScopedRepository[User]):
    model = User


def _context(tenant) -> TenantContext:
    return TenantContext(tenant_id=tenant.id, slug=tenant.slug, name=tenant.name)


async def test_scoped_repository_hides_other_tenants_rows(
    session, tenant, other_tenant, make_user
):
    mine = await make_user(tenant=tenant, email="mine@example.com")
    theirs = await make_user(tenant=other_tenant, email="theirs@example.com")

    repository = _UserScopedRepository(session, _context(tenant))

    assert await repository.get(mine.id) is not None
    # Another tenant's row is indistinguishable from a missing one.
    assert await repository.get(theirs.id) is None


async def test_scoped_repository_stamps_the_context_tenant_on_writes(
    session, tenant, other_tenant
):
    """A caller-supplied tenant_id must not be able to plant a row elsewhere."""
    repository = _UserScopedRepository(session, _context(tenant))

    planted = User(
        tenant_id=other_tenant.id,  # attacker-controlled value
        email="planted@example.com",
        password_hash="x",
        role="CUSTOMER",
        is_active=True,
    )
    await repository.add(planted)
    await session.commit()

    assert planted.tenant_id == tenant.id


async def test_scoped_repository_counts_only_its_own_tenant(
    session, tenant, other_tenant, make_user
):
    await make_user(tenant=tenant, email="a@example.com")
    await make_user(tenant=tenant, email="b@example.com")
    await make_user(tenant=other_tenant, email="c@example.com")

    repository = _UserScopedRepository(session, _context(tenant))

    assert await repository.count() == 2


async def test_unscoped_lookup_still_sees_everything(session, tenant, other_tenant, make_user):
    """Sanity check: the isolation above comes from the scope, not from the data."""
    await make_user(tenant=tenant, email="a@example.com")
    await make_user(tenant=other_tenant, email="c@example.com")

    all_users = (await session.execute(select(User))).scalars().all()
    assert len(all_users) == 2
    assert await UserRepository(session).get_by_tenant_and_email(
        tenant_id=other_tenant.id, email="c@example.com"
    ) is not None
