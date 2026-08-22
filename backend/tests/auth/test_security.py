from __future__ import annotations

import asyncio
import uuid

import jwt
import pytest
from sqlalchemy import select

from app.auth.constants import OTP_LENGTH, UserRole
from app.auth.models import OtpRequest
from app.auth.phone import normalize_phone
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    hash_otp,
    hash_password,
    hash_refresh_token,
    verify_otp,
    verify_password,
)
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from tests.conftest import ADMIN_PASSWORD, request_otp
from tests.conftest import verify_otp as verify_otp_request


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+919876543210", "+919876543210"),
        ("919876543210", "+919876543210"),
        ("09876543210", "+919876543210"),
        ("9876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("+1 (555) 010-0199", "+15550100199"),
        ("  9876543210  ", "+919876543210"),
        ("00447911123456", "+447911123456"),
    ],
)
def test_phone_normalisation(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "12345", "+0123456789", "+", "++4915112345678"])
def test_an_unusable_phone_number_is_refused(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw)


def test_normalisation_is_idempotent():
    once = normalize_phone("09876543210")

    assert normalize_phone(once) == once


async def test_hashing_does_not_block_the_event_loop():
    ticks = 0
    running = True

    async def heartbeat() -> None:
        nonlocal ticks
        while running:
            ticks += 1
            await asyncio.sleep(0.005)

    beat = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.02)

    before = ticks
    await hash_password("a-password-worth-hashing")
    elapsed_ticks = ticks - before

    running = False
    await beat

    assert elapsed_ticks > 5, f"event loop only ticked {elapsed_ticks} times during hashing"


async def test_hash_and_verify_round_trip():
    hashed = await hash_password(ADMIN_PASSWORD)

    assert hashed != ADMIN_PASSWORD
    assert await verify_password(ADMIN_PASSWORD, hashed) is True
    assert await verify_password("not-it", hashed) is False


async def test_hashes_are_salted():
    assert await hash_password(ADMIN_PASSWORD) != await hash_password(ADMIN_PASSWORD)


async def test_malformed_hash_fails_closed():
    assert await verify_password(ADMIN_PASSWORD, "not-a-real-hash") is False


def test_generated_codes_look_right():
    codes = {generate_otp() for _ in range(50)}

    assert all(len(code) == OTP_LENGTH and code.isdigit() for code in codes)
    assert len(codes) > 1


async def test_a_code_round_trips_through_its_hash():
    hashed = await hash_otp("123456")

    assert hashed != "123456"
    assert await verify_otp("123456", hashed) is True
    assert await verify_otp("654321", hashed) is False


def test_an_access_token_carries_its_claims():
    user_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(user_id=user_id, tenant_id=tenant_id, role="ADMIN")

    payload = decode_token(token, expected_type="access")

    assert payload.user_id == str(user_id)
    assert payload.tenant_id == str(tenant_id)
    assert payload.role == "ADMIN"
    assert payload.token_type == "access"


def test_a_refresh_token_is_unique_per_issue():
    user_id, tenant_id = uuid.uuid4(), uuid.uuid4()

    first = create_refresh_token(user_id=user_id, tenant_id=tenant_id)
    second = create_refresh_token(user_id=user_id, tenant_id=tenant_id)

    assert first != second
    assert hash_refresh_token(first) != hash_refresh_token(second)


def test_a_refresh_token_carries_no_role():
    token = create_refresh_token(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    claims = jwt.decode(token, get_settings().jwt_refresh_secret, algorithms=["HS256"])

    assert set(claims) == {"sub", "tenant_id", "type", "jti", "iat", "exp"}


def test_a_tampered_token_is_rejected():
    token = create_access_token(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="CUSTOMER"
    )
    header, payload, signature = token.split(".")

    with pytest.raises(AuthenticationError):
        decode_token(f"{header}.{payload}.{signature[:-2]}xx", expected_type="access")


def test_each_token_type_needs_its_own_secret():
    access = create_access_token(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="STAFF")

    with pytest.raises(AuthenticationError):
        decode_token(access, expected_type="refresh")


def test_a_refresh_token_is_hashed_deterministically():
    token = create_refresh_token(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())

    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert token not in hash_refresh_token(token)


async def test_requesting_codes_is_rate_limited(client, tenant):
    limit = get_settings().otp_request_rate_limit_attempts
    statuses = [
        (await request_otp(client, "+919812345678")).status_code for _ in range(limit + 2)
    ]

    assert statuses[0] == 202
    assert 429 in statuses, statuses


async def test_verifying_codes_is_rate_limited(client, tenant, sent_otps):
    await request_otp(client, "+919812345678")
    limit = get_settings().otp_verify_rate_limit_attempts

    statuses = [
        (await verify_otp_request(client, "+919812345678", "000000")).status_code
        for _ in range(limit + 2)
    ]

    assert 429 in statuses, statuses


async def test_admin_login_is_rate_limited(client, tenant, make_user):
    await make_user(tenant=tenant, email="admin@zeen.com", role=UserRole.ADMIN.value)
    limit = get_settings().login_rate_limit_attempts

    statuses = [
        (
            await client.post(
                "/api/v1/admin/auth/login",
                json={"identifier": "admin@zeen.com", "password": "wrong"},
            )
        ).status_code
        for _ in range(limit + 2)
    ]

    assert statuses[0] == 401
    assert 429 in statuses, statuses


async def test_a_throttled_response_says_when_to_retry(client, tenant):
    for _ in range(get_settings().otp_request_rate_limit_attempts + 3):
        response = await request_otp(client, "+919812345678")
        if response.status_code == 429:
            assert response.json()["error"]["code"] == "RATE_LIMITED"
            assert int(response.headers["Retry-After"]) > 0
            return

    pytest.fail("rate limit never engaged")


async def test_a_successful_verification_clears_the_budget(client, tenant, sent_otps):
    await request_otp(client, "+919812345678")
    for _ in range(3):
        await verify_otp_request(client, "+919812345678", "000000")

    good = await verify_otp_request(client, "+919812345678", sent_otps[-1].otp)
    assert good.status_code == 200


async def test_neither_a_password_nor_a_code_is_stored_in_the_clear(
    client, session, tenant, make_user, sent_otps
):
    admin = await make_user(
        tenant=tenant, email="admin@zeen.com", role=UserRole.ADMIN.value
    )
    await session.refresh(admin)
    assert ADMIN_PASSWORD not in admin.password_hash
    assert admin.password_hash.startswith("$argon2")

    await request_otp(client, "+919812345678")
    record = await session.scalar(select(OtpRequest))
    await session.refresh(record)
    assert sent_otps[-1].otp not in record.otp_hash
    assert record.otp_hash.startswith("$argon2")
