from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.auth.constants import OTP_MAX_ATTEMPTS, OtpPurpose, UserRole, UserStatus
from app.auth.models import AdminAuthChallenge, OtpRequest
from tests.conftest import admin_login, sign_in_admin, sign_in_staff

VERIFY = "/api/v1/admin/auth/verify-otp"

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


async def test_a_correct_staff_password_sends_a_code(client, staff, sent_otps):
    response = await admin_login(client, STAFF_EMAIL)

    assert response.status_code == 202
    assert response.json()["message"] == "OTP sent"
    assert response.json()["data"]["verification_id"]
    assert sent_otps[-1].phone == STAFF_PHONE


async def test_staff_login_works_by_phone_or_email(client, staff, sent_otps):
    assert (await admin_login(client, STAFF_EMAIL)).status_code == 202
    assert (await admin_login(client, STAFF_PHONE)).status_code == 202
    assert (await admin_login(client, "09800000002")).status_code == 202


async def test_staff_step_one_issues_no_credential(client, staff, sent_otps):
    body = (await admin_login(client, STAFF_EMAIL)).json()["data"]

    assert set(body) == {"verification_id"}
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['verification_id']}"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "identifier", [ADMIN_EMAIL, "ghost@zeen.com", "+919000000999", "nonsense"]
)
async def test_a_wrong_password_never_says_why(client, admin, identifier, sent_otps):
    response = await admin_login(client, identifier, password="not-the-password")

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid credentials"
    assert not sent_otps


async def test_an_inactive_admin_cannot_log_in(client, tenant, make_user, sent_otps):
    await make_user(
        tenant=tenant,
        email="off@zeen.com",
        role=UserRole.ADMIN.value,
        status=UserStatus.INACTIVE.value,
    )

    response = await admin_login(client, "off@zeen.com")

    assert response.status_code == 401
    assert not sent_otps


async def test_a_customer_cannot_use_the_admin_door(client, tenant, user, sent_otps):
    response = await admin_login(client, user.phone)

    assert response.status_code == 401
    assert not sent_otps


async def test_a_correct_staff_code_issues_tokens(client, staff, sent_otps):
    tokens = await sign_in_staff(client, sent_otps, STAFF_EMAIL)

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


async def test_a_wrong_staff_code_is_rejected(client, staff, sent_otps):
    verification_id = await challenge_id(client)
    otp = sent_otps[-1].otp
    wrong = "000000" if otp != "000000" else "111111"

    response = await client.post(
        VERIFY, json={"verification_id": verification_id, "otp": wrong}
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid or expired OTP"


async def test_an_expired_staff_code_is_rejected(client, session, staff, sent_otps):
    verification_id = await challenge_id(client)
    record = await session.scalar(select(OtpRequest))
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await session.commit()

    response = await client.post(
        VERIFY, json={"verification_id": verification_id, "otp": sent_otps[-1].otp}
    )

    assert response.status_code == 401


async def test_an_expired_staff_challenge_is_rejected(client, session, staff, sent_otps):
    verification_id = await challenge_id(client)
    challenge = await session.scalar(select(AdminAuthChallenge))
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await session.commit()

    response = await client.post(
        VERIFY, json={"verification_id": verification_id, "otp": sent_otps[-1].otp}
    )

    assert response.status_code == 401


async def test_a_staff_challenge_cannot_be_used_twice(client, staff, sent_otps):
    verification_id = await challenge_id(client)
    payload = {"verification_id": verification_id, "otp": sent_otps[-1].otp}

    assert (await client.post(VERIFY, json=payload)).status_code == 200
    assert (await client.post(VERIFY, json=payload)).status_code == 401


async def test_staff_logging_in_again_retires_the_previous_challenge(
    client, staff, sent_otps
):
    first = await challenge_id(client)
    second = await challenge_id(client)
    assert first != second

    stale = await client.post(
        VERIFY, json={"verification_id": first, "otp": sent_otps[-1].otp}
    )
    assert stale.status_code == 401

    fresh = await client.post(
        VERIFY, json={"verification_id": second, "otp": sent_otps[-1].otp}
    )
    assert fresh.status_code == 200


async def test_a_staff_code_dies_after_too_many_wrong_guesses(client, staff, sent_otps):
    verification_id = await challenge_id(client)
    otp = sent_otps[-1].otp
    wrong = "000000" if otp != "000000" else "111111"

    for _ in range(OTP_MAX_ATTEMPTS):
        response = await client.post(
            VERIFY, json={"verification_id": verification_id, "otp": wrong}
        )
        assert response.status_code == 401

    replayed = await client.post(
        VERIFY, json={"verification_id": verification_id, "otp": otp}
    )
    assert replayed.status_code == 401


async def test_an_unknown_verification_id_is_rejected(client, staff):
    response = await client.post(
        VERIFY,
        json={
            "verification_id": "00000000-0000-0000-0000-000000000000",
            "otp": "123456",
        },
    )

    assert response.status_code == 401


async def test_a_customers_code_cannot_be_redeemed_at_the_admin_endpoint(
    client, session, user, sent_otps
):
    await client.post("/api/v1/auth/otp/request", json={"phone": user.phone})
    customer_code = await session.scalar(
        select(OtpRequest).where(OtpRequest.purpose == OtpPurpose.CUSTOMER_LOGIN.value)
    )
    assert customer_code is not None

    response = await client.post(
        VERIFY,
        json={"verification_id": str(customer_code.id), "otp": sent_otps[-1].otp},
    )

    assert response.status_code == 401


async def test_a_staff_code_cannot_be_redeemed_at_the_customer_endpoint(
    client, staff, sent_otps
):
    await admin_login(client, STAFF_EMAIL)

    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": STAFF_PHONE, "otp": sent_otps[-1].otp},
    )

    assert response.status_code == 401


async def test_a_staff_user_deactivated_between_the_steps_gets_nothing(
    client, session, staff, sent_otps
):
    verification_id = await challenge_id(client)

    staff.status = UserStatus.INACTIVE.value
    await session.commit()

    response = await client.post(
        VERIFY, json={"verification_id": verification_id, "otp": sent_otps[-1].otp}
    )

    assert response.status_code == 401


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
