"""Guarantees the database enforces on its own, independent of application code."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.constants import UserRole
from app.tenants.models import Tenant
from app.users.models import User


def _user(tenant_id, email: str, role: str = UserRole.CUSTOMER.value) -> User:
    return User(
        tenant_id=tenant_id,
        email=email,
        password_hash="not-a-real-hash",
        role=role,
        is_active=True,
    )


async def test_email_is_unique_within_a_tenant(session, tenant):
    session.add(_user(tenant.id, "dup@example.com"))
    await session.commit()

    session.add(_user(tenant.id, "dup@example.com"))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_same_email_allowed_across_tenants(session, tenant, other_tenant):
    session.add(_user(tenant.id, "shared@example.com"))
    session.add(_user(other_tenant.id, "shared@example.com"))

    await session.commit()  # must not raise

    rows = (await session.execute(select(User))).scalars().all()
    assert len(rows) == 2


async def test_tenant_slug_is_unique(session, tenant):
    session.add(Tenant(name="Copy", slug="zeen", is_active=True))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_role_must_be_a_known_value(session, tenant):
    """ck_users_role_valid stops an invented role reaching the table."""
    session.add(_user(tenant.id, "bad-role@example.com", role="SUPER_DUPER_ADMIN"))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.parametrize("role", [r.value for r in UserRole])
async def test_every_application_role_is_accepted(session, tenant, role):
    """The check constraint and the UserRole enum must not drift apart."""
    session.add(_user(tenant.id, f"{role.lower()}@example.com", role=role))

    await session.commit()  # must not raise


async def test_deleting_a_tenant_cascades_to_its_users(session, tenant, other_tenant):
    session.add(_user(tenant.id, "doomed@example.com"))
    session.add(_user(other_tenant.id, "survivor@example.com"))
    await session.commit()

    await session.delete(tenant)
    await session.commit()

    remaining = (await session.execute(select(User))).scalars().all()
    assert [u.email for u in remaining] == ["survivor@example.com"]


async def test_platform_users_may_have_no_tenant(session):
    session.add(_user(None, "platform@example.com", role=UserRole.PLATFORM_ADMIN.value))

    await session.commit()  # must not raise


async def test_defaults_are_applied(session, tenant):
    user = User(
        tenant_id=tenant.id,
        email="defaults@example.com",
        password_hash="not-a-real-hash",
    )
    session.add(user)
    await session.commit()

    # A missing role must fall back to the LEAST privileged role, not an admin one.
    assert user.role == UserRole.CUSTOMER.value
    assert user.is_active is True
    assert user.created_at is not None


async def test_timestamps_are_server_generated(session, tenant):
    user = _user(tenant.id, "stamped@example.com")
    session.add(user)
    await session.commit()

    assert user.created_at is not None
    assert user.updated_at is not None


async def test_user_ids_are_not_sequential(session, tenant):
    """IDs are UUIDs, so one user's id does not let you guess another's."""
    first = _user(tenant.id, "one@example.com")
    second = _user(tenant.id, "two@example.com")
    session.add_all([first, second])
    await session.commit()

    assert isinstance(first.id, uuid.UUID)
    assert first.id != second.id
