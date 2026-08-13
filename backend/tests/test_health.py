"""Health probes and the global response-envelope contract."""

from __future__ import annotations

import pytest


async def test_liveness_has_no_dependencies(client):
    """Liveness must not fail because a datastore is briefly unavailable."""
    response = await client.get("/health")

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
    response = await client.get("/health")

    assert response.headers["X-Request-Id"]


async def test_supplied_request_id_is_echoed(client):
    response = await client.get("/health", headers={"X-Request-Id": "trace-me"})

    assert response.headers["X-Request-Id"] == "trace-me"


@pytest.mark.parametrize(
    "payload",
    [
        {"tenant_slug": "zeen", "email": "not-an-email", "password": "hunter2hunter2"},
        {"tenant_slug": "zeen", "email": "a@b.com"},
    ],
)
async def test_validation_errors_never_echo_the_password(client, payload):
    """A rejected request must not round-trip the submitted password."""
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "hunter2hunter2" not in response.text
