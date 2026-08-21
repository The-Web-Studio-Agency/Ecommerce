from __future__ import annotations

import pytest


def body_is_enveloped(response) -> bool:
    body = response.json()
    return body["success"] is False and body["error"]["code"] in {
        "VALIDATION_ERROR",
        "AUTHENTICATION_FAILED",
    }


async def test_unknown_route_uses_the_error_envelope(client):
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "payload",
    [
        {"identifier": "not-an-email", "password": "hunter2hunter2"},
        {"password": "hunter2hunter2"},
        {"identifier": "a@b.com"},
    ],
)
async def test_validation_errors_never_echo_the_password(client, tenant, payload):
    response = await client.post("/api/v1/admin/auth/login", json=payload)

    assert response.status_code in (401, 422)
    assert body_is_enveloped(response)
    assert "hunter2hunter2" not in response.text


async def test_validation_errors_never_echo_a_one_time_code(client, tenant):
    response = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": "not-a-phone", "otp": "123456"}
    )

    assert response.status_code == 422
    assert body_is_enveloped(response)
    assert "123456" not in response.text
