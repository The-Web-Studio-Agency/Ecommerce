"""Test fixtures.

The suite runs against a real PostgreSQL database (the constraints under test -
composite uniqueness, the role check, ON DELETE CASCADE - are database
behaviour, and SQLite would not reproduce them). The test database is created
once per session from `TEST_DATABASE_URL` and dropped at the end; every test
gets a clean set of tables.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.constants import UserRole
from app.auth.security import hash_password
from app.core import cache
from app.core.config import get_settings
from app.core.database import get_db
from app.tenants.models import Tenant
from app.users.models import User

# The registry, not app.models.base: it is what imports every model module, so
# Base.metadata knows about every table. Importing the base alone would create
# a schema missing whichever models no other import happened to pull in.
from app.models.registry import Base  # isort: skip

settings = get_settings()

TEST_DATABASE_URL = settings.test_database_url or (
    settings.database_url.rsplit("/", 1)[0] + "/tws_ecommerce_test"
)


def _admin_url(url: str) -> str:
    """Point a database URL at the `postgres` maintenance database."""
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
    """A clean schema plus a session, per test."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(loop_scope="session")
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """An HTTP client bound to the app, sharing the test's database session."""
    from app.main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _flush_rate_limiter() -> AsyncGenerator[None, None]:
    """Rate-limit counters live in Redis and would otherwise leak between tests."""
    with contextlib.suppress(Exception):  # Redis is optional for most tests
        await cache.get_redis().flushdb()
    yield


# ----------------------------------------------------------------- factories


@pytest_asyncio.fixture(loop_scope="session")
async def tenant(session: AsyncSession) -> Tenant:
    tenant = Tenant(name="Zeen", slug="zeen", is_active=True)
    session.add(tenant)
    await session.commit()
    return tenant


@pytest_asyncio.fixture(loop_scope="session")
async def other_tenant(session: AsyncSession) -> Tenant:
    tenant = Tenant(name="Acme", slug="acme", is_active=True)
    session.add(tenant)
    await session.commit()
    return tenant


USER_PASSWORD = "correct-horse-battery"


@pytest_asyncio.fixture(loop_scope="session")
async def make_user(session: AsyncSession):
    async def _make(
        *,
        tenant: Tenant | None,
        email: str = "user@zeen.com",
        password: str = USER_PASSWORD,
        role: str | None = None,
        is_active: bool = True,
    ) -> User:
        # ck_users_role_matches_tenant_scope: platform users have no tenant and
        # every other role has one, so the default role follows the tenant.
        if role is None:
            role = (
                UserRole.CUSTOMER.value if tenant is not None else UserRole.PLATFORM_ADMIN.value
            )
        user = User(
            tenant_id=tenant.id if tenant else None,
            email=email,
            password_hash=await hash_password(password),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        await session.commit()
        return user

    return _make


@pytest_asyncio.fixture(loop_scope="session")
async def user(make_user, tenant: Tenant) -> User:
    return await make_user(tenant=tenant)


async def login(client: AsyncClient, *, slug: str, email: str, password: str):
    return await client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": slug, "email": email, "password": password},
    )


async def access_token_for(client: AsyncClient, *, slug: str, email: str, password: str) -> str:
    response = await login(client, slug=slug, email=email, password=password)
    assert response.status_code == 200, response.text
    return response.json()["data"]["tokens"]["access_token"]


async def headers_for(client: AsyncClient, *, slug: str, email: str) -> dict[str, str]:
    """Bearer header obtained by actually logging in.

    Tenant-scoped modules are tested through the full chain - login, token,
    user row, permission - rather than with a hand-minted token.
    """
    token = await access_token_for(client, slug=slug, email=email, password=USER_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(loop_scope="session")
async def admin_headers(client, tenant, make_user) -> dict[str, str]:
    """A TENANT_ADMIN of the `tenant` fixture (slug "zeen")."""
    await make_user(tenant=tenant, email="admin@zeen.com", role=UserRole.TENANT_ADMIN.value)
    return await headers_for(client, slug=tenant.slug, email="admin@zeen.com")


@pytest_asyncio.fixture(loop_scope="session")
async def other_admin_headers(client, other_tenant, make_user) -> dict[str, str]:
    """A TENANT_ADMIN of the `other_tenant` fixture (slug "acme")."""
    await make_user(
        tenant=other_tenant, email="admin@acme.com", role=UserRole.TENANT_ADMIN.value
    )
    return await headers_for(client, slug=other_tenant.slug, email="admin@acme.com")
