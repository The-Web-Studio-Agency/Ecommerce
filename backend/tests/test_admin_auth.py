from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.auth.constants import OTP_MAX_ATTEMPTS, OtpPurpose, UserRole, UserStatus
from app.auth.models import AdminAuthChallenge, OtpRequest
from tests.conftest import admin_login, sign_in_admin, sign_in_staff

VERIFY = "/api/v1/staff/auth/verify-otp"

ADMIN_PHONE = "+919800000001"
ADMIN_EMAIL = "admin@zeen.com"
STAFF_PHONE = "+919800000002"
STAFF_EMAIL = "staff@zeen.com"


@pytest_asyncio.fixture(loop_scope="session")
async def admin(tenant, make_user):
    return await make_user(
        tenant=tenant,
        phone=ADMIN_PHONE,
        email=ADMIN_EMAIL,
        name="Ada",
        role=UserRole.ADMIN.value,
    )


@pytest_asyncio.fixture(loop_scope="session")
async def staff(tenant, make_user):
    return await make_user(
        tenant=tenant,
        phone=STAFF_PHONE,
        email=STAFF_EMAIL,
        name="Grace",
        role=UserRole.STAFF.value,
    )


async def challenge_id(client, identifier: str = STAFF_EMAIL) -> str:
    response = await admin_login(client, identifier)
    assert response.status_code == 202, response.text
    return response.json()["data"]["verification_id"]


async def test_a_correct_admin_password_issues_tokens_without_a_code(client, admin, sent_otps):
    response = await admin_login(client, ADMIN_EMAIL)

    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    data = response.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert "verification_id" not in data
    assert not sent_otps


async def test_admin_login_works_by_phone_or_email(client, admin, sent_otps):
    assert (await admin_login(client, ADMIN_EMAIL)).status_code == 200
    assert (await admin_login(client, ADMIN_PHONE)).status_code == 200
    assert (await admin_login(client, "09800000001")).status_code == 200
    assert not sent_otps


async def test_admin_login_token_authenticates_immediately(client, admin, sent_otps):
    body = (await admin_login(client, ADMIN_EMAIL)).json()["data"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert response.status_code == 200
    assert not sent_otps


async def test_staff_password_login_returns_tokens(client, staff, sent_otps):
    response = await client.post(
        "/api/v1/staff/auth/login",
        json={"identifier": STAFF_EMAIL, "password": "correct-horse-battery"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    data = response.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert not sent_otps


async def test_staff_login_works_by_phone_or_email(client, staff, sent_otps):
    assert (
        await client.post(
            "/api/v1/staff/auth/login",
            json={"identifier": STAFF_EMAIL, "password": "correct-horse-battery"},
        )
    ).status_code == 200
    assert (
        await client.post(
            "/api/v1/staff/auth/login",
            json={"identifier": STAFF_PHONE, "password": "correct-horse-battery"},
        )
    ).status_code == 200
    assert (
        await client.post(
            "/api/v1/staff/auth/login",
            json={"identifier": "09800000002", "password": "correct-horse-battery"},
        )
    ).status_code == 200


async def test_staff_token_authenticates_immediately(client, staff, sent_otps):
    body = (
        await client.post(
            "/api/v1/staff/auth/login",
            json={"identifier": STAFF_EMAIL, "password": "correct-horse-battery"},
        )
    ).json()["data"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert response.status_code == 200
    assert not sent_otps


async def test_an_admin_token_reaches_admin_endpoints(client, admin):
    tokens = await sign_in_admin(client, ADMIN_EMAIL)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.post(
        "/api/v1/catalogue/categories",
        json={"name": "Dresses", "slug": "dresses"},
        headers=headers,
    )

    assert response.status_code == 201


async def test_the_profile_reports_the_admin(client, admin):
    tokens = await sign_in_admin(client, ADMIN_EMAIL)

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    data = response.json()["data"]
    assert data["role"] == UserRole.ADMIN.value
    assert data["email"] == ADMIN_EMAIL
    assert data["name"] == "Ada"


async def test_staff_can_sign_in_too(client, tenant, make_user, sent_otps):
    await make_user(tenant=tenant, email="staff@zeen.com", role=UserRole.STAFF.value)

    tokens = await sign_in_staff(client, sent_otps, "staff@zeen.com")

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.json()["data"]["role"] == UserRole.STAFF.value
