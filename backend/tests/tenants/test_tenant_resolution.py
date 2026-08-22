from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.constants import UserRole
from app.auth.models import OtpRequest
from app.core.config import get_settings
from app.tenants.models import TenantDomain
from app.tenants.repository import TenantRepository
from app.tenants.resolver import normalize_hostname
from app.users.models import User
from tests.conftest import ACME_DOMAIN, UNREGISTERED_DOMAIN, ZEEN_DOMAIN


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("www.abc.com", "www.abc.com"),
        ("WWW.ABC.COM", "www.abc.com"),
        ("  www.abc.com  ", "www.abc.com"),
        ("www.abc.com:8000", "www.abc.com"),
        ("www.abc.com.", "www.abc.com"),
        ("localhost:3000", "localhost"),
        ("[::1]:8000", "[::1]"),
        ("", None),
        (None, None),
        (":8000", None),
    ],
)
def test_hostname_normalisation(raw, expected):
    assert normalize_hostname(raw) == expected


async def test_a_registered_domain_resolves_to_its_tenant(session, tenant):
    resolved = await TenantRepository(session).get_active_by_domain(ZEEN_DOMAIN)

    assert resolved is not None
    assert resolved.id == tenant.id


async def test_several_domains_may_serve_one_tenant(session, tenant):
    session.add(TenantDomain(tenant_id=tenant.id, domain="zeen.example"))
    await session.commit()

    tenants = TenantRepository(session)
    assert (await tenants.get_active_by_domain("zeen.example")).id == tenant.id
    assert (await tenants.get_active_by_domain(ZEEN_DOMAIN)).id == tenant.id


async def test_an_unregistered_domain_resolves_to_nothing(session, tenant):
    assert await TenantRepository(session).get_active_by_domain(UNREGISTERED_DOMAIN) is None


async def test_a_suspended_tenants_domain_stops_resolving(session, tenant):
    tenant.is_active = False
    await session.commit()

    assert await TenantRepository(session).get_active_by_domain(ZEEN_DOMAIN) is None


async def test_a_domain_belongs_to_one_tenant_only(session, tenant, other_tenant):
    session.add(TenantDomain(tenant_id=other_tenant.id, domain=ZEEN_DOMAIN))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_requests_to_an_unregistered_domain_are_rejected(client, tenant):
    response = await client.get("/api/v1/auth/me", headers={"Host": UNREGISTERED_DOMAIN})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "UNKNOWN_STOREFRONT"


async def test_the_domain_is_resolved_before_authentication(client, tenant):
    unknown = await client.get(
        "/api/v1/catalogue/products", headers={"Host": UNREGISTERED_DOMAIN}
    )
    known = await client.get("/api/v1/catalogue/products")

    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "UNKNOWN_STOREFRONT"
    assert known.status_code == 401


async def test_a_port_in_the_host_header_still_resolves(client, tenant):
    response = await request_otp_on(client, f"{ZEEN_DOMAIN}:8000")

    assert response.status_code == 202


async def test_localhost_user_creation_falls_back_to_the_first_active_tenant(
    client, session, tenant
):
    response = await client.post(
        "/api/v1/users/admin",
        json={
            "email": "local@admin.com",
            "phone": "+919000000001",
            "name": "Local Admin",
            "password": "Passw0rd!",
        },
        headers={"Host": "localhost"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()["data"]
    assert payload["email"] == "local@admin.com"
    assert payload["role"] == UserRole.ADMIN.value

    record = await session.scalar(select(User).where(User.email == "local@admin.com"))
    assert record is not None
    assert record.tenant_id == tenant.id


async def test_host_matching_is_case_insensitive(client, tenant):
    response = await request_otp_on(client, ZEEN_DOMAIN.upper())

    assert response.status_code == 202


async def request_otp_on(client, host: str):
    return await client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+919777000111"},
        headers={"Host": host},
    )


async def test_the_forwarded_host_is_ignored_by_default(client, tenant, other_tenant):
    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+919777000222"},
        headers={"Host": ZEEN_DOMAIN, "X-Forwarded-Host": ACME_DOMAIN},
    )

    assert response.status_code == 202


async def test_the_forwarded_host_is_used_when_the_proxy_is_trusted(
    client, session, tenant, other_tenant, monkeypatch
):
    monkeypatch.setattr(get_settings(), "trust_forwarded_host", True)

    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+919777000333"},
        headers={"Host": "internal.lb", "X-Forwarded-Host": ACME_DOMAIN},
    )

    assert response.status_code == 202
    record = await session.scalar(select(OtpRequest))
    assert record.tenant_id == other_tenant.id


async def test_only_the_first_forwarded_host_is_read(
    client, session, tenant, other_tenant, monkeypatch
):
    monkeypatch.setattr(get_settings(), "trust_forwarded_host", True)

    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+919777000444"},
        headers={"Host": "internal.lb", "X-Forwarded-Host": f"{ZEEN_DOMAIN}, {ACME_DOMAIN}"},
    )

    assert response.status_code == 202
    record = await session.scalar(select(OtpRequest))
    assert record.tenant_id == tenant.id


async def test_an_untrusted_forwarded_host_cannot_reach_an_unregistered_tenant(
    client, tenant
):
    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+919777000555"},
        headers={"Host": UNREGISTERED_DOMAIN, "X-Forwarded-Host": ZEEN_DOMAIN},
    )

    assert response.status_code == 404
