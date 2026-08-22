from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.constants import UserRole, UserStatus
from app.auth.security import create_access_token, hash_password
from app.core import cache
from app.core.config import get_settings
from app.core.database import get_db
from app.models.registry import Base
from app.tenants.models import Tenant, TenantDomain
from app.users.models import User
from tests.helpers import shared_data

settings = get_settings()

TEST_DATABASE_URL = settings.test_database_url or (
    settings.database_url.rsplit("/", 1)[0] + "/tws_ecommerce_test"
)

_SHARED = shared_data()

ZEEN_DOMAIN = _SHARED["domains"]["zeen"]
ACME_DOMAIN = _SHARED["domains"]["acme"]
UNREGISTERED_DOMAIN = _SHARED["domains"]["unregistered"]

ADMIN_PASSWORD = _SHARED["passwords"]["admin"]


def _admin_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path="/postgres"))


def _database_name(url: str) -> str:
    return urlsplit(url).path.lstrip("/")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _create_test_database() -> AsyncGenerator[None, None]:
    name = _database_name(TEST_DATABASE_URL)
    admin = create_async_engine(_admin_url(TEST_DATABASE_URL), isolation_level="AUTOCOMMIT")

    async with admin.connect() as connection:
        await connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    await admin.dispose()

    yield

    admin = create_async_engine(_admin_url(TEST_DATABASE_URL), isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        await connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    await admin.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine(_create_test_database):
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=None)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _client_for(session: AsyncSession, domain: str) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=f"http://{domain}") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async for c in _client_for(session, ZEEN_DOMAIN):
        yield c


@pytest_asyncio.fixture(loop_scope="session")
async def other_client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async for c in _client_for(session, ACME_DOMAIN):
        yield c


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _flush_rate_limiter() -> AsyncGenerator[None, None]:
    with contextlib.suppress(Exception):
        await cache.get_redis().flushdb()
    yield


@dataclass(frozen=True)
class SentOtp:
    phone: str
    otp: str


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def sent_otps(monkeypatch) -> list[SentOtp]:
    delivered: list[SentOtp] = []

    async def capture(phone: str, otp: str) -> None:
        delivered.append(SentOtp(phone=phone, otp=otp))

    monkeypatch.setattr("app.auth.service.send_otp", capture)
    return delivered


@pytest_asyncio.fixture(loop_scope="session")
async def tenant(session: AsyncSession) -> Tenant:
    tenant = Tenant(name="Zeen", slug="zeen", is_active=True)
    session.add(tenant)
    await session.flush()
    session.add(TenantDomain(tenant_id=tenant.id, domain=ZEEN_DOMAIN))
    await session.commit()
    return tenant


@pytest_asyncio.fixture(loop_scope="session")
async def other_tenant(session: AsyncSession) -> Tenant:
    tenant = Tenant(name="Acme", slug="acme", is_active=True)
    session.add(tenant)
    await session.flush()
    session.add(TenantDomain(tenant_id=tenant.id, domain=ACME_DOMAIN))
    await session.commit()
    return tenant


@pytest_asyncio.fixture(loop_scope="session")
async def make_user(session: AsyncSession):
    counter = {"n": 0}

    async def _make(
        *,
        tenant: Tenant,
        phone: str | None = None,
        email: str | None = None,
        name: str | None = None,
        role: str = UserRole.CUSTOMER.value,
        password: str = ADMIN_PASSWORD,
        status: str = UserStatus.ACTIVE.value,
    ) -> User:
        counter["n"] += 1
        is_staff = role != UserRole.CUSTOMER.value

        if phone is None:
            phone = f"+91900000{counter['n']:04d}"
        user = User(
            tenant_id=tenant.id,
            phone=phone,
            email=email,
            name=name,
            role=role,
            status=status,
            password_hash=await hash_password(password) if is_staff else None,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        return user

    return _make


@pytest_asyncio.fixture(loop_scope="session")
async def user(make_user, tenant: Tenant) -> User:
    return await make_user(tenant=tenant, phone="+919876543210")


def token_for(user: User) -> str:
    return create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)


def headers_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user)}"}


async def request_otp(client: AsyncClient, phone: str):
    return await client.post("/api/v1/auth/otp/request", json={"phone": phone})


async def verify_otp(client: AsyncClient, phone: str, otp: str):
    return await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})


async def sign_in_customer(client: AsyncClient, sent_otps: list[SentOtp], phone: str) -> dict:
    requested = await request_otp(client, phone)
    assert requested.status_code == 202, requested.text

    response = await verify_otp(client, phone, sent_otps[-1].otp)
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def admin_login(
    client: AsyncClient,
    identifier: str,
    password: str = ADMIN_PASSWORD,
):
    return await client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": identifier, "password": password},
    )


async def sign_in_admin(
    client: AsyncClient,
    identifier: str,
    password: str = ADMIN_PASSWORD,
) -> dict:
    response = await admin_login(client, identifier, password)
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def sign_in_staff(
    client: AsyncClient,
    sent_otps: list[SentOtp],
    identifier: str,
    password: str = ADMIN_PASSWORD,
) -> dict:
    response = await client.post(
        "/api/v1/staff/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest_asyncio.fixture(loop_scope="session")
async def admin_headers(tenant, make_user) -> dict[str, str]:
    admin = await make_user(
        tenant=tenant, email="admin@zeen.com", role=UserRole.ADMIN.value
    )
    return headers_for(admin)


@pytest_asyncio.fixture(loop_scope="session")
async def staff_headers(tenant, make_user) -> dict[str, str]:
    staff = await make_user(
        tenant=tenant, email="staff@zeen.com", role=UserRole.STAFF.value
    )
    return headers_for(staff)


@pytest_asyncio.fixture(loop_scope="session")
async def customer_headers(tenant, make_user) -> dict[str, str]:
    customer = await make_user(tenant=tenant, phone="+919000111222")
    return headers_for(customer)


@pytest_asyncio.fixture(loop_scope="session")
async def other_admin_headers(other_tenant, make_user) -> dict[str, str]:
    admin = await make_user(
        tenant=other_tenant, email="admin@acme.com", role=UserRole.ADMIN.value
    )
    return headers_for(admin)
