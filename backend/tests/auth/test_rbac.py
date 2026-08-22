from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import UserRole, UserStatus
from app.auth.dependencies import require_admin, require_staff
from app.auth.security import create_access_token
from app.core.database import get_db
from app.main import create_app
from app.users.models import User
from tests.conftest import ZEEN_DOMAIN, headers_for

ADMIN_ONLY = "/rbac/admin-only"
STAFF_OR_ABOVE = "/rbac/staff-or-above"


@pytest_asyncio.fixture(loop_scope="session")
async def rbac_client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    router = APIRouter()

    async def admin_only(_: User = Depends(require_admin)) -> dict:
        return {"allowed": True}

    async def staff_or_above(_: User = Depends(require_staff)) -> dict:
        return {"allowed": True}

    router.add_api_route(ADMIN_ONLY, admin_only, methods=["GET"])
    router.add_api_route(STAFF_OR_ABOVE, staff_or_above, methods=["GET"])
    app.include_router(router)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=f"http://{ZEEN_DOMAIN}") as client:
        yield client
    app.dependency_overrides.clear()


async def _get(client: AsyncClient, path: str, user: User) -> int:
    response = await client.get(path, headers=headers_for(user))
    return response.status_code


@pytest.mark.parametrize(
    ("role", "path", "expected"),
    [
        (UserRole.ADMIN, ADMIN_ONLY, 200),
        (UserRole.ADMIN, STAFF_OR_ABOVE, 200),
        (UserRole.STAFF, ADMIN_ONLY, 403),
        (UserRole.STAFF, STAFF_OR_ABOVE, 200),
        (UserRole.CUSTOMER, ADMIN_ONLY, 403),
        (UserRole.CUSTOMER, STAFF_OR_ABOVE, 403),
    ],
)
async def test_the_role_matrix(rbac_client, tenant, make_user, role, path, expected):
    user = await make_user(tenant=tenant, role=role.value)

    assert await _get(rbac_client, path, user) == expected


async def test_an_admin_counts_as_staff(rbac_client, tenant, make_user):
    admin = await make_user(tenant=tenant, role=UserRole.ADMIN.value, email="a@zeen.com")

    assert await _get(rbac_client, STAFF_OR_ABOVE, admin) == 200


async def test_an_anonymous_caller_is_rejected(rbac_client, tenant):
    assert (await rbac_client.get(ADMIN_ONLY)).status_code == 401


async def test_permission_denied_uses_the_error_envelope(rbac_client, tenant, make_user):
    customer = await make_user(tenant=tenant)

    response = await rbac_client.get(ADMIN_ONLY, headers=headers_for(customer))

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PERMISSION_DENIED"
    assert body["message"] == "Insufficient permissions"


async def test_a_forged_role_claim_grants_nothing(rbac_client, tenant, make_user):
    customer = await make_user(tenant=tenant)
    forged = create_access_token(
        user_id=customer.id,
        tenant_id=customer.tenant_id,
        role=UserRole.ADMIN.value,
    )

    response = await rbac_client.get(ADMIN_ONLY, headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 403


async def test_a_deactivated_admin_loses_access(rbac_client, session, tenant, make_user):
    admin = await make_user(tenant=tenant, role=UserRole.ADMIN.value, email="gone@zeen.com")
    assert await _get(rbac_client, ADMIN_ONLY, admin) == 200

    admin.status = UserStatus.INACTIVE.value
    await session.commit()

    assert await _get(rbac_client, ADMIN_ONLY, admin) == 401


async def test_a_demoted_admin_loses_access_immediately(
    rbac_client, session, tenant, make_user
):
    admin = await make_user(tenant=tenant, role=UserRole.ADMIN.value, email="demote@zeen.com")
    headers = headers_for(admin)
    assert (await rbac_client.get(ADMIN_ONLY, headers=headers)).status_code == 200

    admin.role = UserRole.STAFF.value
    await session.commit()

    assert (await rbac_client.get(ADMIN_ONLY, headers=headers)).status_code == 403
    assert (await rbac_client.get(STAFF_OR_ABOVE, headers=headers)).status_code == 200
