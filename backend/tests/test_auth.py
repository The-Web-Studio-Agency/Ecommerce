from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.auth.constants import OTP_MAX_ATTEMPTS, UserRole, UserStatus
from app.auth.models import OtpRequest
from app.auth.security import create_access_token, create_refresh_token
from app.core.config import get_settings
from app.users.models import User
from tests.conftest import (
    headers_for,
    request_otp,
    sign_in_customer,
    verify_otp,
)

PHONE = "+919812345678"


def auth_header(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_requesting_a_code_sends_one(client, tenant, sent_otps):
    response = await request_otp(client, PHONE)

    assert response.status_code == 202
    assert response.json()["message"] == "OTP sent"
    assert sent_otps[-1].phone == PHONE
    assert len(sent_otps[-1].otp) == 6
    assert sent_otps[-1].otp.isdigit()


async def test_the_response_is_the_same_whether_or_not_an_account_exists(
    client, tenant, user, sent_otps
):
    known = await request_otp(client, user.phone)
    unknown = await request_otp(client, "+919555000111")

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


@pytest.mark.parametrize(
    "typed",
    ["+919876543210", "919876543210", "09876543210", "9876543210", "+91 98765 43210"],
)
async def test_one_phone_number_however_it_is_typed(client, tenant, user, sent_otps, typed):
    response = await request_otp(client, typed)

    assert response.status_code == 202
    assert sent_otps[-1].phone == "+919876543210"


@pytest.mark.parametrize("phone", ["not-a-phone", "12", "+0123456789", "++9198765"])
async def test_an_unusable_phone_number_is_rejected(client, tenant, phone):
    response = await request_otp(client, phone)

    assert response.status_code == 422


async def test_requesting_again_invalidates_the_previous_code(client, tenant, sent_otps):
    await request_otp(client, PHONE)
    first = sent_otps[-1].otp

    await request_otp(client, PHONE)
    second = sent_otps[-1].otp
    assert first != second

    stale = await verify_otp(client, PHONE, first)
    assert stale.status_code == 401

    fresh = await verify_otp(client, PHONE, second)
    assert fresh.status_code == 200


async def test_a_valid_code_returns_a_token_pair(client, tenant, sent_otps):
    tokens = await sign_in_customer(client, sent_otps, PHONE)

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] > 0


async def test_a_wrong_code_is_rejected(client, tenant, sent_otps):
    await request_otp(client, PHONE)
    wrong = "000000" if sent_otps[-1].otp != "000000" else "111111"

    response = await verify_otp(client, PHONE, wrong)

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid or expired OTP"


async def test_an_expired_code_is_rejected(client, session, tenant, sent_otps):
    await request_otp(client, PHONE)
    record = await session.scalar(select(OtpRequest))
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await session.commit()

    response = await verify_otp(client, PHONE, sent_otps[-1].otp)

    assert response.status_code == 401


async def test_a_code_cannot_be_used_twice(client, tenant, sent_otps):
    await request_otp(client, PHONE)
    otp = sent_otps[-1].otp

    assert (await verify_otp(client, PHONE, otp)).status_code == 200
    assert (await verify_otp(client, PHONE, otp)).status_code == 401


async def test_a_code_dies_after_too_many_wrong_guesses(client, tenant, sent_otps):
    await request_otp(client, PHONE)
    otp = sent_otps[-1].otp
    wrong = "000000" if otp != "000000" else "111111"

    for _ in range(OTP_MAX_ATTEMPTS):
        assert (await verify_otp(client, PHONE, wrong)).status_code == 401

    assert (await verify_otp(client, PHONE, otp)).status_code == 401


async def test_a_failed_attempt_is_recorded(client, session, tenant, sent_otps):
    await request_otp(client, PHONE)
    await verify_otp(client, PHONE, "000000")

    record = await session.scalar(select(OtpRequest))
    await session.refresh(record)
    assert record.attempts == 1


async def test_verifying_without_ever_requesting_is_rejected(client, tenant):
    response = await verify_otp(client, PHONE, "123456")

    assert response.status_code == 401


@pytest.mark.parametrize("otp", ["12345", "1234567", "abcdef", ""])
async def test_a_malformed_code_is_rejected(client, tenant, otp):
    response = await verify_otp(client, PHONE, otp)

    assert response.status_code == 422


async def test_a_first_time_customer_gets_an_account(client, session, tenant, sent_otps):
    await sign_in_customer(client, sent_otps, PHONE)

    created = await session.scalar(select(User).where(User.phone == PHONE))
    assert created is not None
    assert created.tenant_id == tenant.id
    assert created.role == UserRole.CUSTOMER.value
    assert created.is_verified is True
    assert created.password_hash is None


async def test_an_existing_customer_is_signed_in_not_duplicated(
    client, session, tenant, user, sent_otps
):
    tokens = await sign_in_customer(client, sent_otps, user.phone)

    me = await client.get("/api/v1/auth/me", headers=auth_header(tokens))
    assert me.json()["data"]["id"] == str(user.id)

    rows = (await session.execute(select(User).where(User.phone == user.phone))).scalars().all()
    assert len(rows) == 1


async def test_a_deactivated_customer_cannot_sign_in(client, session, tenant, user, sent_otps):
    user.status = UserStatus.INACTIVE.value
    await session.commit()

    await request_otp(client, user.phone)
    response = await verify_otp(client, user.phone, sent_otps[-1].otp)

    assert response.status_code == 401


async def test_a_staff_account_cannot_use_the_passwordless_door(
    client, tenant, make_user, sent_otps
):
    admin = await make_user(
        tenant=tenant, email="admin@zeen.com", role=UserRole.ADMIN.value
    )

    await request_otp(client, admin.phone)
    response = await verify_otp(client, admin.phone, sent_otps[-1].otp)

    assert response.status_code == 401


async def test_verification_marks_the_account_verified(client, session, tenant, sent_otps):
    await sign_in_customer(client, sent_otps, PHONE)

    created = await session.scalar(select(User).where(User.phone == PHONE))
    assert created.is_verified is True


async def test_the_access_token_authenticates_a_request(client, tenant, user, sent_otps):
    tokens = await sign_in_customer(client, sent_otps, user.phone)

    response = await client.get("/api/v1/auth/me", headers=auth_header(tokens))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(user.id)
    assert data["phone"] == user.phone
    assert data["role"] == UserRole.CUSTOMER.value


async def test_missing_token_rejected(client, tenant):
    assert (await client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.parametrize("token", ["", "not-a-jwt", "eyJhbGciOiJIUzI1NiJ9.e30.bad-signature"])
async def test_invalid_token_rejected(client, tenant, token):
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


async def test_expired_token_rejected(client, tenant, user, monkeypatch):
    monkeypatch.setattr(get_settings(), "access_token_expire_minutes", -1)
    expired = create_access_token(user_id=user.id, tenant_id=tenant.id, role=user.role)

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


async def test_refresh_token_rejected_as_access_token(client, tenant, user):
    refresh = create_refresh_token(user_id=user.id, tenant_id=tenant.id)

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"})

    assert response.status_code == 401


async def test_token_rejected_after_the_user_is_deactivated(client, session, tenant, user):
    headers = headers_for(user)
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200

    user.status = UserStatus.INACTIVE.value
    await session.commit()

    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401


async def test_the_access_token_carries_nothing_personal(client, tenant, user, sent_otps):
    import jwt

    tokens = await sign_in_customer(client, sent_otps, user.phone)
    claims = jwt.decode(
        tokens["access_token"], get_settings().jwt_secret, algorithms=["HS256"]
    )

    assert set(claims) == {"sub", "tenant_id", "role", "type", "iat", "exp"}
    assert claims["sub"] == str(user.id)
    assert claims["tenant_id"] == str(tenant.id)


async def test_refresh_issues_a_new_token_pair(client, tenant, user, sent_otps):
    tokens = await sign_in_customer(client, sent_otps, user.phone)

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


async def test_access_token_rejected_as_refresh_token(client, tenant, user, sent_otps):
    tokens = await sign_in_customer(client, sent_otps, user.phone)

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )

    assert response.status_code == 401


async def test_rotation_invalidates_the_previous_refresh_token(client, tenant, user, sent_otps):
    first = (await sign_in_customer(client, sent_otps, user.phone))["refresh_token"]

    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert rotated.status_code == 200
    second = rotated.json()["data"]["refresh_token"]
    assert second != first

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401


async def test_reuse_of_a_rotated_token_revokes_every_session(client, tenant, user, sent_otps):
    first = (await sign_in_customer(client, sent_otps, user.phone))["refresh_token"]
    second = (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    ).json()["data"]["refresh_token"]

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401

    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": second})
    assert after.status_code == 401


async def test_refresh_rejected_after_the_user_is_deactivated(
    client, session, tenant, user, sent_otps
):
    tokens = await sign_in_customer(client, sent_otps, user.phone)

    user.status = UserStatus.INACTIVE.value
    await session.commit()

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


async def test_logout_revokes_the_refresh_token(client, tenant, user, sent_otps):
    tokens = await sign_in_customer(client, sent_otps, user.phone)

    logged_out = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logged_out.status_code == 204

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


async def test_logout_is_not_an_oracle(client, tenant, user, sent_otps):
    tokens = await sign_in_customer(client, sent_otps, user.phone)
    refresh_token = tokens["refresh_token"]

    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    ).status_code == 204
    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    ).status_code == 204
    never_issued = create_refresh_token(user_id=user.id, tenant_id=tenant.id)
    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": never_issued})
    ).status_code == 204


async def test_logout_does_not_disturb_another_session(client, tenant, user, sent_otps):
    first = (await sign_in_customer(client, sent_otps, user.phone))["refresh_token"]
    second = (await sign_in_customer(client, sent_otps, user.phone))["refresh_token"]

    await client.post("/api/v1/auth/logout", json={"refresh_token": first})

    still_valid = await client.post("/api/v1/auth/refresh", json={"refresh_token": second})
    assert still_valid.status_code == 200
