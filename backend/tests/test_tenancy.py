from __future__ import annotations

from sqlalchemy import select

from app.auth.constants import OtpPurpose, UserRole
from app.auth.models import OtpRequest
from app.auth.security import create_access_token
from app.users.models import User
from app.users.repository import UserRepository
from tests.conftest import (
    ADMIN_PASSWORD,
    headers_for,
    request_otp,
    sign_in_customer,
    verify_otp,
)

SHARED_PHONE = "+919876500001"


async def test_the_same_phone_may_exist_in_both_tenants(
    client, other_client, session, tenant, other_tenant, sent_otps
):
    zeen = await sign_in_customer(client, sent_otps, SHARED_PHONE)
    acme = await sign_in_customer(other_client, sent_otps, SHARED_PHONE)

    rows = (
        (await session.execute(select(User).where(User.phone == SHARED_PHONE)))
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert {row.tenant_id for row in rows} == {tenant.id, other_tenant.id}
    assert zeen["access_token"] != acme["access_token"]


async def test_a_lookup_needs_the_right_tenant(session, tenant, other_tenant, make_user):
    theirs = await make_user(tenant=other_tenant, phone=SHARED_PHONE)
    users = UserRepository(session)

    assert (
        await users.get_by_phone(tenant_id=other_tenant.id, phone=SHARED_PHONE)
    ).id == theirs.id
    assert await users.get_by_phone(tenant_id=tenant.id, phone=SHARED_PHONE) is None


async def test_a_lookup_by_id_is_tenant_scoped(session, tenant, other_tenant, make_user):
    theirs = await make_user(tenant=other_tenant)
    users = UserRepository(session)

    assert await users.get_by_id(tenant_id=other_tenant.id, user_id=theirs.id) is not None
    assert await users.get_by_id(tenant_id=tenant.id, user_id=theirs.id) is None


async def test_a_token_from_one_tenant_is_useless_at_another(
    client, other_client, tenant, other_tenant, user
):
    headers = headers_for(user)

    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    assert (await other_client.get("/api/v1/auth/me", headers=headers)).status_code == 401


async def test_a_token_from_one_tenant_cannot_reach_another_tenants_data(
    client, other_client, tenant, other_tenant, admin_headers, other_admin_headers
):
    created = await client.post(
        "/api/v1/catalogue/categories",
        json={"name": "Dresses", "slug": "dresses"},
        headers=admin_headers,
    )
    assert created.status_code == 201

    blocked = await other_client.get("/api/v1/catalogue/categories", headers=admin_headers)
    assert blocked.status_code == 401

    theirs = await other_client.get(
        "/api/v1/catalogue/categories", headers=other_admin_headers
    )
    assert theirs.status_code == 200
    assert theirs.json()["meta"]["total_items"] == 0


async def test_a_forged_tenant_claim_is_refused(client, tenant, other_tenant, make_user):
    intruder = await make_user(tenant=other_tenant)
    forged = create_access_token(
        user_id=intruder.id, tenant_id=tenant.id, role=intruder.role
    )

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"}
    )

    assert response.status_code == 401


async def test_a_header_cannot_move_the_caller(client, tenant, other_tenant, user):
    response = await client.get(
        "/api/v1/auth/me",
        headers={**headers_for(user), "X-Tenant-Slug": "acme", "X-Tenant-Id": str(other_tenant.id)},
    )

    assert response.status_code == 200
    assert response.json()["data"]["tenant_id"] == str(tenant.id)


async def test_query_parameters_cannot_move_the_caller(client, tenant, other_tenant, user):
    response = await client.get(
        "/api/v1/auth/me",
        params={"tenant_id": str(other_tenant.id), "tenant_slug": "acme"},
        headers=headers_for(user),
    )

    assert response.status_code == 200
    assert response.json()["data"]["tenant_id"] == str(tenant.id)


async def test_codes_are_scoped_to_the_tenant_that_issued_them(
    client, other_client, tenant, other_tenant, sent_otps
):
    await request_otp(client, SHARED_PHONE)
    zeen_code = sent_otps[-1].otp

    crossed = await verify_otp(other_client, SHARED_PHONE, zeen_code)
    assert crossed.status_code == 401

    assert (await verify_otp(client, SHARED_PHONE, zeen_code)).status_code == 200


async def test_an_otp_row_belongs_to_one_tenant(client, session, tenant, sent_otps):
    await request_otp(client, SHARED_PHONE)

    record = await session.scalar(
        select(OtpRequest).where(OtpRequest.purpose == OtpPurpose.CUSTOMER_LOGIN.value)
    )
    assert record.tenant_id == tenant.id


async def test_a_refresh_token_cannot_be_rotated_at_another_storefront(
    client, other_client, tenant, other_tenant, user, sent_otps
):
    tokens = await sign_in_customer(client, sent_otps, user.phone)

    crossed = await other_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert crossed.status_code == 401

    assert (
        await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
    ).status_code == 200


async def test_a_refresh_token_cannot_be_revoked_from_another_storefront(
    client, other_client, tenant, other_tenant, user, sent_otps
):
    tokens = await sign_in_customer(client, sent_otps, user.phone)

    await other_client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )

    assert (
        await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
    ).status_code == 200


async def test_suspending_one_tenant_does_not_affect_another(
    client, other_client, session, tenant, other_tenant, sent_otps
):
    tenant.is_active = False
    await session.commit()

    blocked = await request_otp(client, SHARED_PHONE)
    assert blocked.status_code == 404
    assert blocked.json()["error"]["code"] == "UNKNOWN_STOREFRONT"

    assert (await request_otp(other_client, "+919555000222")).status_code == 202


async def test_users_from_both_tenants_coexist(session, tenant, other_tenant, make_user):
    await make_user(tenant=tenant)
    await make_user(tenant=other_tenant, role=UserRole.ADMIN.value, email="a@acme.com")

    all_users = (await session.execute(select(User))).scalars().all()

    assert len(all_users) == 2
    assert {u.tenant_id for u in all_users} == {tenant.id, other_tenant.id}


async def test_the_domain_decides_which_tenant_a_new_customer_joins(
    client, other_client, session, tenant, other_tenant, sent_otps
):
    await sign_in_customer(other_client, sent_otps, SHARED_PHONE)

    created = await session.scalar(select(User).where(User.phone == SHARED_PHONE))
    assert created.tenant_id == other_tenant.id


async def test_a_staff_challenge_from_one_tenant_cannot_be_verified_at_another(
    client, other_client, tenant, other_tenant, make_user, sent_otps
):
    await make_user(tenant=tenant, email="staff@zeen.com", role=UserRole.STAFF.value)

    challenge = await client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": "staff@zeen.com", "password": ADMIN_PASSWORD},
    )
    assert challenge.status_code == 202
    verification_id = challenge.json()["data"]["verification_id"]
    otp = sent_otps[-1].otp

    crossed = await other_client.post(
        "/api/v1/admin/auth/verify-otp",
        json={"verification_id": verification_id, "otp": otp},
    )
    assert crossed.status_code == 401

    intact = await client.post(
        "/api/v1/admin/auth/verify-otp",
        json={"verification_id": verification_id, "otp": otp},
    )
    assert intact.status_code == 200


async def test_presenting_a_token_to_the_wrong_tenant_does_not_revoke_it(
    client, other_client, tenant, other_tenant, user, sent_otps
):
    tokens = await sign_in_customer(client, sent_otps, user.phone)

    for _ in range(3):
        crossed = await other_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert crossed.status_code == 401

    still_valid = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert still_valid.status_code == 200


async def test_a_user_id_from_one_tenant_does_not_resolve_at_another(
    client, other_client, tenant, other_tenant, make_user
):
    theirs = await make_user(tenant=other_tenant, email="admin@acme.com", role=UserRole.ADMIN.value)

    forged = create_access_token(
        user_id=theirs.id, tenant_id=tenant.id, role=theirs.role
    )

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"}
    )

    assert response.status_code == 401
