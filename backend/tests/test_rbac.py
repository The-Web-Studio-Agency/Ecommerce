"""Role-based authorization: what each role may and may not do.

`require_permission` has no production route yet - the modules it will guard
(catalogue, inventory, orders) are not built. The guard is nonetheless the
mechanism every one of those modules will depend on, so it is exercised here
against routes mounted only for the test, using the real dependency and the
real application error handling.

Tokens are minted directly rather than obtained from /auth/login because the
subject under test is authorization, not the login flow - and because a
PLATFORM_ADMIN cannot log in through the tenant-scoped login endpoint at all.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import UserRole
from app.auth.permissions import Permission, permissions_for_role, require_permission
from app.auth.security import create_access_token
from app.core.database import get_db
from app.main import create_app

# One route per permission that distinguishes the roles from each other.
_GUARDED_ROUTES = {
    "/rbac/catalogue-create": Permission.CATALOGUE_CREATE,
    "/rbac/inventory-update": Permission.INVENTORY_UPDATE,
    "/rbac/platform-tenants": Permission.PLATFORM_TENANTS_MANAGE,
}


@pytest_asyncio.fixture(loop_scope="session")
async def rbac_client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """A client for an app carrying the guarded test routes."""
    app = create_app()
    router = APIRouter()

    for path, permission in _GUARDED_ROUTES.items():
        # Default argument binds the permission per iteration.
        async def endpoint(_: object = Depends(require_permission(permission))) -> dict:
            return {"allowed": True}

        router.add_api_route(path, endpoint, methods=["GET"])

    app.include_router(router)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _token(user) -> str:
    return create_access_token(
        subject=str(user.id),
        role=user.role,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
    )


async def _get(client: AsyncClient, path: str, user) -> int:
    response = await client.get(path, headers={"Authorization": f"Bearer {_token(user)}"})
    return response.status_code


# --------------------------------------------------------- the role/permission table


@pytest.mark.parametrize(
    ("role", "permission", "granted"),
    [
        (UserRole.TENANT_ADMIN, Permission.CATALOGUE_CREATE, True),
        (UserRole.TENANT_ADMIN, Permission.INVENTORY_UPDATE, True),
        (UserRole.TENANT_ADMIN, Permission.PLATFORM_TENANTS_MANAGE, False),
        (UserRole.STAFF, Permission.CATALOGUE_READ, True),
        (UserRole.STAFF, Permission.INVENTORY_UPDATE, True),
        (UserRole.STAFF, Permission.CATALOGUE_CREATE, False),
        (UserRole.STAFF, Permission.CATALOGUE_DELETE, False),
        (UserRole.STAFF, Permission.PAYMENTS_MANAGE, False),
        (UserRole.CUSTOMER, Permission.CATALOGUE_READ, False),
        (UserRole.CUSTOMER, Permission.ORDERS_READ, False),
        (UserRole.PLATFORM_ADMIN, Permission.PLATFORM_TENANTS_MANAGE, True),
        (UserRole.PLATFORM_ADMIN, Permission.CATALOGUE_CREATE, False),
    ],
)
def test_role_permission_table(role, permission, granted):
    """The mapping itself, independent of HTTP."""
    assert (permission in permissions_for_role(role.value)) is granted


def test_customers_hold_no_back_office_permission():
    assert permissions_for_role(UserRole.CUSTOMER.value) == frozenset()


def test_an_unknown_role_grants_nothing():
    """A role that is not in the table must fail closed, not open."""
    assert permissions_for_role("WAREHOUSE_ROBOT") == frozenset()


# ------------------------------------------------------------------- enforcement


async def test_tenant_admin_may_perform_permitted_operations(rbac_client, tenant, make_user):
    admin = await make_user(
        tenant=tenant, email="admin@zeen.com", role=UserRole.TENANT_ADMIN.value
    )

    assert await _get(rbac_client, "/rbac/catalogue-create", admin) == 200
    assert await _get(rbac_client, "/rbac/inventory-update", admin) == 200


async def test_staff_cannot_perform_admin_only_operations(rbac_client, tenant, make_user):
    """Staff move stock; they do not restructure the catalogue."""
    staff = await make_user(tenant=tenant, email="staff@zeen.com", role=UserRole.STAFF.value)

    assert await _get(rbac_client, "/rbac/inventory-update", staff) == 200
    assert await _get(rbac_client, "/rbac/catalogue-create", staff) == 403


async def test_customer_cannot_access_admin_operations(rbac_client, tenant, make_user):
    customer = await make_user(
        tenant=tenant, email="customer@zeen.com", role=UserRole.CUSTOMER.value
    )

    assert await _get(rbac_client, "/rbac/catalogue-create", customer) == 403
    assert await _get(rbac_client, "/rbac/inventory-update", customer) == 403


async def test_platform_admin_may_perform_platform_operations(rbac_client, make_user):
    platform_admin = await make_user(
        tenant=None, email="platform@tws.com", role=UserRole.PLATFORM_ADMIN.value
    )

    assert await _get(rbac_client, "/rbac/platform-tenants", platform_admin) == 200


async def test_tenant_admin_cannot_perform_platform_operations(rbac_client, tenant, make_user):
    """The tenant boundary is a ceiling as well as a wall."""
    admin = await make_user(
        tenant=tenant, email="admin2@zeen.com", role=UserRole.TENANT_ADMIN.value
    )

    assert await _get(rbac_client, "/rbac/platform-tenants", admin) == 403


async def test_guarded_route_rejects_an_anonymous_caller(rbac_client):
    response = await rbac_client.get("/rbac/catalogue-create")

    assert response.status_code == 401


async def test_permission_denied_uses_the_error_envelope(rbac_client, tenant, make_user):
    customer = await make_user(
        tenant=tenant, email="envelope@zeen.com", role=UserRole.CUSTOMER.value
    )

    response = await rbac_client.get(
        "/rbac/catalogue-create", headers={"Authorization": f"Bearer {_token(customer)}"}
    )

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PERMISSION_DENIED"


async def test_a_forged_role_claim_does_not_grant_permission(rbac_client, tenant, make_user):
    """The role comes from the database row, never from the JWT claim.

    This is the difference between a permission system and a suggestion: a
    token that says PLATFORM_ADMIN for a user whose row says CUSTOMER must be
    authorised as a CUSTOMER.
    """
    customer = await make_user(
        tenant=tenant, email="forger@zeen.com", role=UserRole.CUSTOMER.value
    )
    forged = create_access_token(
        subject=str(customer.id),
        role=UserRole.TENANT_ADMIN.value,  # lie
        tenant_id=str(customer.tenant_id),
    )

    response = await rbac_client.get(
        "/rbac/catalogue-create", headers={"Authorization": f"Bearer {forged}"}
    )

    assert response.status_code == 403


async def test_a_deactivated_admin_loses_access(rbac_client, session, tenant, make_user):
    """Authorization re-checks user state, so a live token is not a free pass."""
    admin = await make_user(
        tenant=tenant, email="revoked@zeen.com", role=UserRole.TENANT_ADMIN.value
    )
    assert await _get(rbac_client, "/rbac/catalogue-create", admin) == 200

    admin.is_active = False
    await session.commit()

    assert await _get(rbac_client, "/rbac/catalogue-create", admin) == 401
