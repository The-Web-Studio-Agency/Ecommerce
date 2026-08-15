"""Password hashing, token handling and login throttling."""

from __future__ import annotations

import asyncio

import pytest

from app.auth.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.exceptions import AuthenticationError
from tests.conftest import USER_PASSWORD, login


async def test_hashing_does_not_block_the_event_loop():
    """Argon2 must run in a worker thread, not inline on the event loop.

    Argon2id costs ~250ms of CPU per call. Run inline, it freezes every other
    in-flight request on the worker for that whole time and caps the process at
    roughly four logins per second. The heartbeat below keeps ticking only if
    the hash is off-loop.
    """
    ticks = 0
    running = True

    async def heartbeat() -> None:
        nonlocal ticks
        while running:
            ticks += 1
            await asyncio.sleep(0.005)

    beat = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.02)  # let the heartbeat establish itself

    before = ticks
    await hash_password("a-password-worth-hashing")
    elapsed_ticks = ticks - before

    running = False
    await beat

    # Inline hashing would leave the loop no chance to tick at all.
    assert elapsed_ticks > 5, f"event loop only ticked {elapsed_ticks} times during hashing"



async def test_hash_and_verify_round_trip():
    hashed = await hash_password(USER_PASSWORD)

    assert hashed != USER_PASSWORD
    assert await verify_password(USER_PASSWORD, hashed) is True
    assert await verify_password("not-it", hashed) is False


async def test_hashes_are_salted():
    assert await hash_password(USER_PASSWORD) != await hash_password(USER_PASSWORD)


async def test_malformed_hash_fails_closed():
    """A corrupt stored hash is a failed login, never a 500."""
    assert await verify_password(USER_PASSWORD, "not-a-real-hash") is False


# ------------------------------------------------------------------ tokens


def test_access_token_carries_its_claims():
    token = create_access_token(subject="abc", role="CUSTOMER", tenant_id="t-1")

    payload = decode_token(token, expected_type="access")

    assert payload.subject == "abc"
    assert payload.role == "CUSTOMER"
    assert payload.tenant_id == "t-1"
    assert payload.token_type == "access"
    assert payload.jti


def test_tokens_are_unique_per_issue():
    first = create_access_token(subject="abc", role=None, tenant_id=None)
    second = create_access_token(subject="abc", role=None, tenant_id=None)

    assert decode_token(first, expected_type="access").jti != (
        decode_token(second, expected_type="access").jti
    )


def test_tampered_token_is_rejected():
    token = create_access_token(subject="abc", role="CUSTOMER", tenant_id=None)
    header, payload, signature = token.split(".")

    with pytest.raises(AuthenticationError):
        decode_token(f"{header}.{payload}.{signature[:-2]}xx", expected_type="access")


# ----------------------------------------------------------- rate limiting


async def test_repeated_failed_logins_are_throttled(client, tenant, user):
    """Argon2's cost makes an unthrottled login a cheap denial-of-service vector."""
    limit = 10
    statuses = [
        (
            await login(client, slug="zeen", email=user.email, password="wrong-password")
        ).status_code
        for _ in range(limit + 2)
    ]

    assert statuses[0] == 401
    assert 429 in statuses, statuses


async def test_throttling_response_says_when_to_retry(client, tenant, user):
    for _ in range(12):
        response = await login(client, slug="zeen", email=user.email, password="wrong-password")
        if response.status_code == 429:
            assert response.json()["error"]["code"] == "RATE_LIMITED"
            assert int(response.headers["Retry-After"]) > 0
            return

    pytest.fail("rate limit never engaged")


async def test_a_successful_login_clears_the_counter(client, tenant, user):
    for _ in range(5):
        await login(client, slug="zeen", email=user.email, password="wrong-password")

    good = await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)
    assert good.status_code == 200

    # The budget is restored, so the next few attempts are not immediately blocked.
    again = await login(client, slug="zeen", email=user.email, password="wrong-password")
    assert again.status_code == 401
