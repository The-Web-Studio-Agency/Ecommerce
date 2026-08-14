"""Authentication behaviour: login, registration, refresh and token validity."""

from __future__ import annotations

import pytest

from app.auth.constants import UserRole
from app.auth.security import create_access_token, create_refresh_token
from app.core.config import get_settings
from tests.conftest import USER_PASSWORD, access_token_for, login

LONG_PASSWORD = "p" * 200


# ------------------------------------------------------------------- login


async def test_login_succeeds(client, tenant, user):
    response = await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["tokens"]["access_token"]
    assert body["data"]["tokens"]["refresh_token"]
    assert body["data"]["user"]["email"] == user.email


@pytest.mark.parametrize(
    ("slug", "email", "password"),
    [
        ("nope", "user@zeen.com", USER_PASSWORD),  # unknown tenant
        ("zeen", "ghost@zeen.com", USER_PASSWORD),  # unknown user
        ("zeen", "user@zeen.com", "wrong-password"),  # wrong password
    ],
)
async def test_login_failures_are_indistinguishable(client, tenant, user, slug, email, password):
    """Unknown tenant, unknown user and wrong password must look identical."""
    response = await login(client, slug=slug, email=email, password=password)

    assert response.status_code == 401
    body = response.json()
    assert body["message"] == "Invalid credentials"
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"


async def test_login_inactive_user_rejected(client, tenant, make_user):
    inactive = await make_user(tenant=tenant, email="off@zeen.com", is_active=False)

    response = await login(client, slug="zeen", email=inactive.email, password=USER_PASSWORD)

    assert response.status_code == 401


async def test_login_inactive_tenant_rejected(client, session, tenant, user):
    tenant.is_active = False
    await session.commit()

    response = await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)

    assert response.status_code == 401


# ------------------------------------------------------------ registration


async def test_registration_creates_a_customer(client, tenant):
    response = await client.post(
        "/api/v1/auth/register",
        json={"tenant_slug": "zeen", "email": "New@Zeen.com", "password": "a-good-password"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["role"] == UserRole.CUSTOMER.value
    # Email is normalised on the way in so it cannot collide by case later.
    assert data["email"] == "new@zeen.com"


@pytest.mark.parametrize("role", [r.value for r in UserRole])
async def test_role_escalation_via_payload_is_impossible(client, tenant, role):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": "zeen",
            "email": f"{role.lower()}@zeen.com",
            "password": "a-good-password",
            "role": role,
        },
    )

    assert response.status_code == 201
    assert response.json()["data"]["role"] == UserRole.CUSTOMER.value


async def test_duplicate_email_in_same_tenant_rejected(client, tenant, user):
    response = await client.post(
        "/api/v1/auth/register",
        json={"tenant_slug": "zeen", "email": user.email, "password": "a-good-password"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


async def test_registration_unknown_tenant_rejected(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"tenant_slug": "ghost", "email": "a@b.com", "password": "a-good-password"},
    )

    assert response.status_code == 404


async def test_short_password_is_rejected(client, tenant):
    response = await client.post(
        "/api/v1/auth/register",
        json={"tenant_slug": "zeen", "email": "short@zeen.com", "password": "abc"},
    )

    assert response.status_code == 422


async def test_a_password_that_can_be_registered_can_also_be_used_to_log_in(client, tenant):
    """Registration and login must agree on the maximum password length.

    Regression: registration allowed 256 characters while login capped at 128,
    so any account created with a longer password could never authenticate.
    """
    registered = await client.post(
        "/api/v1/auth/register",
        json={"tenant_slug": "zeen", "email": "long@zeen.com", "password": LONG_PASSWORD},
    )
    assert registered.status_code == 201

    response = await login(client, slug="zeen", email="long@zeen.com", password=LONG_PASSWORD)
    assert response.status_code == 200


# ------------------------------------------------------------------ tokens


async def test_valid_access_token_works(client, tenant, user):
    token = await access_token_for(client, slug="zeen", email=user.email, password=USER_PASSWORD)

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(user.id)


async def test_missing_token_rejected(client):
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.parametrize("token", ["", "not-a-jwt", "eyJhbGciOiJIUzI1NiJ9.e30.bad-signature"])
async def test_invalid_token_rejected(client, token):
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


async def test_expired_token_rejected(client, tenant, user, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
    expired = create_access_token(subject=str(user.id), role=user.role, tenant_id=str(tenant.id))

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


async def test_refresh_token_rejected_as_access_token(client, tenant, user):
    """Separate signing secrets mean a refresh token cannot authenticate a request."""
    refresh = create_refresh_token(subject=str(user.id), role=user.role, tenant_id=str(tenant.id))

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"})

    assert response.status_code == 401


async def test_token_rejected_after_user_deactivated(client, session, tenant, user):
    token = await access_token_for(client, slug="zeen", email=user.email, password=USER_PASSWORD)

    user.is_active = False
    await session.commit()

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_token_rejected_after_tenant_deactivated(client, session, tenant, user):
    """Deactivating a tenant must take effect immediately, not at token expiry."""
    token = await access_token_for(client, slug="zeen", email=user.email, password=USER_PASSWORD)

    tenant.is_active = False
    await session.commit()

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


# ----------------------------------------------------------------- refresh


async def test_refresh_issues_a_new_token_pair(client, tenant, user):
    tokens = (
        await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)
    ).json()["data"]["tokens"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    assert response.json()["data"]["tokens"]["access_token"]


async def test_access_token_rejected_as_refresh_token(client, tenant, user):
    token = await access_token_for(client, slug="zeen", email=user.email, password=USER_PASSWORD)

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})

    assert response.status_code == 401


async def test_refresh_rejected_after_tenant_deactivated(client, session, tenant, user):
    tokens = (
        await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)
    ).json()["data"]["tokens"]

    tenant.is_active = False
    await session.commit()

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


# -------------------------------------------------- rotation and revocation


async def test_rotation_invalidates_the_previous_refresh_token(client, tenant, user):
    """A refresh token is single-use: rotating it spends it."""
    first = (
        await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)
    ).json()["data"]["tokens"]["refresh_token"]

    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert rotated.status_code == 200
    second = rotated.json()["data"]["tokens"]["refresh_token"]
    assert second != first

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401


async def test_reuse_of_a_rotated_token_revokes_every_session(client, tenant, user):
    """Replay means two parties hold the token, so every session is cut.

    This is the whole point of rotation: the replay itself is the signal, and
    because we cannot tell the legitimate client from the thief, the live
    token issued by the rotation must die too.
    """
    first = (
        await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)
    ).json()["data"]["tokens"]["refresh_token"]

    second = (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    ).json()["data"]["tokens"]["refresh_token"]

    # The attacker (or the client) replays the already-spent token.
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401

    # The still-live token from the rotation is now dead as well.
    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": second})
    assert after.status_code == 401


async def test_logout_revokes_the_refresh_token(client, tenant, user):
    refresh_token = (
        await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)
    ).json()["data"]["tokens"]["refresh_token"]

    logged_out = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logged_out.status_code == 204

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


async def test_logout_is_not_an_oracle(client, tenant, user):
    """Unknown and already-revoked tokens must look exactly like valid ones."""
    refresh_token = (
        await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)
    ).json()["data"]["tokens"]["refresh_token"]

    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    ).status_code == 204
    # Same token again - already revoked.
    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    ).status_code == 204
    # A token this server never issued.
    never_issued = create_refresh_token(subject=str(user.id), role=user.role, tenant_id=None)
    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": never_issued})
    ).status_code == 204


async def test_logout_does_not_disturb_another_session(client, tenant, user):
    """Logging out one session must not sign the user out everywhere."""
    first = (
        await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)
    ).json()["data"]["tokens"]["refresh_token"]
    second = (
        await login(client, slug="zeen", email=user.email, password=USER_PASSWORD)
    ).json()["data"]["tokens"]["refresh_token"]

    await client.post("/api/v1/auth/logout", json={"refresh_token": first})

    still_valid = await client.post("/api/v1/auth/refresh", json={"refresh_token": second})
    assert still_valid.status_code == 200
