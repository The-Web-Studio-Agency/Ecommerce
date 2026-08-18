from __future__ import annotations

import pytest


async def test_liveness_has_no_dependencies(client):
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_readiness_reports_each_dependency(client):
    response = await client.get("/health/ready")

    assert response.status_code in (200, 503)
    checks = response.json()["checks"]
    assert set(checks) == {"database", "redis"}


async def test_unknown_route_uses_the_error_envelope(client):
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


async def test_every_response_carries_a_request_id(client):
    response = await client.get("/health/live")

    assert response.headers["X-Request-Id"]


async def test_supplied_request_id_is_echoed(client):
    response = await client.get("/health/live", headers={"X-Request-Id": "trace-me"})

    assert response.headers["X-Request-Id"] == "trace-me"


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


def body_is_enveloped(response) -> bool:
    body = response.json()
    return body["success"] is False and body["error"]["code"] in {
        "VALIDATION_ERROR",
        "AUTHENTICATION_FAILED",
    }
