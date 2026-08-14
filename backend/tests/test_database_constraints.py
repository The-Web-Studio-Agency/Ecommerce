"""Guarantees the database enforces on its own, independent of application code."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.constants import UserRole
from app.catalogue.constants import CatalogueStatus
from app.catalogue.models import Category, Product, ProductVariant
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
    """The check constraint and the UserRole enum must not drift apart.

    Each role is inserted at the tenant scope it is actually defined for:
    ck_users_role_matches_tenant_scope requires PLATFORM_ADMIN to have no
    tenant and every other role to have one, so a single fixed scope could
    not satisfy the whole enum.
    """
    is_platform = role == UserRole.PLATFORM_ADMIN.value
    tenant_id = None if is_platform else tenant.id
    session.add(_user(tenant_id, f"{role.lower()}@example.com", role=role))

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


# ----------------------------------------------------------------- catalogue


def _category(tenant_id, slug: str = "dresses", name: str = "Dresses") -> Category:
    return Category(tenant_id=tenant_id, name=name, slug=slug, is_active=True)


def _product(tenant_id, category_id, slug: str = "dress", name: str = "Dress") -> Product:
    return Product(
        tenant_id=tenant_id,
        category_id=category_id,
        name=name,
        slug=slug,
        status=CatalogueStatus.DRAFT.value,
    )


def _variant(tenant_id, product_id, sku: str = "SKU-1", price: str = "10.00") -> ProductVariant:
    return ProductVariant(
        tenant_id=tenant_id,
        product_id=product_id,
        sku=sku,
        name="Small / Black",
        price=Decimal(price),
        status=CatalogueStatus.DRAFT.value,
    )


async def test_a_product_cannot_reference_another_tenants_category(
    session, tenant, other_tenant
):
    """The composite foreign key, not the service, is the last line here.

    Even with the application bypassed entirely, a product in one tenant cannot
    point at a category in another.
    """
    category = _category(tenant.id)
    session.add(category)
    await session.commit()

    session.add(_product(other_tenant.id, category.id))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_variant_cannot_reference_another_tenants_product(
    session, tenant, other_tenant
):
    category = _category(tenant.id)
    session.add(category)
    await session.commit()
    product = _product(tenant.id, category.id)
    session.add(product)
    await session.commit()

    session.add(_variant(other_tenant.id, product.id))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_category_slug_is_unique_within_a_tenant(session, tenant):
    session.add(_category(tenant.id))
    await session.commit()

    session.add(_category(tenant.id))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_the_same_category_slug_is_allowed_across_tenants(
    session, tenant, other_tenant
):
    session.add_all([_category(tenant.id), _category(other_tenant.id)])

    await session.commit()  # must not raise


async def test_a_sku_is_unique_within_a_tenant(session, tenant):
    category = _category(tenant.id)
    session.add(category)
    await session.commit()
    product = _product(tenant.id, category.id)
    session.add(product)
    await session.commit()

    session.add(_variant(tenant.id, product.id))
    await session.commit()
    session.add(_variant(tenant.id, product.id))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("slug", "Dresses"),      # ck_categories_slug_is_lowercase
        ("name", "   "),          # ck_categories_name_not_blank
    ],
)
async def test_category_check_constraints_reject_bad_values(session, tenant, field, value):
    category = _category(tenant.id)
    setattr(category, field, value)
    session.add(category)

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_product_status_must_be_a_known_value(session, tenant):
    category = _category(tenant.id)
    session.add(category)
    await session.commit()

    product = _product(tenant.id, category.id)
    product.status = "ON_FIRE"
    session.add(product)

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_negative_price_is_rejected_by_the_database(session, tenant):
    """Pydantic checks this too; the column must not depend on that."""
    category = _category(tenant.id)
    session.add(category)
    await session.commit()
    product = _product(tenant.id, category.id)
    session.add(product)
    await session.commit()

    session.add(_variant(tenant.id, product.id, price="-1.00"))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_lowercase_sku_is_rejected_by_the_database(session, tenant):
    category = _category(tenant.id)
    session.add(category)
    await session.commit()
    product = _product(tenant.id, category.id)
    session.add(product)
    await session.commit()

    session.add(_variant(tenant.id, product.id, sku="sku-lower"))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_deleting_a_product_cascades_to_its_variants(session, tenant):
    category = _category(tenant.id)
    session.add(category)
    await session.commit()
    product = _product(tenant.id, category.id)
    session.add(product)
    await session.commit()
    session.add(_variant(tenant.id, product.id))
    await session.commit()

    await session.delete(product)
    await session.commit()

    remaining = (await session.execute(select(ProductVariant))).scalars().all()
    assert remaining == []


async def test_deleting_a_category_in_use_is_refused(session, tenant):
    category = _category(tenant.id)
    session.add(category)
    await session.commit()
    session.add(_product(tenant.id, category.id))
    await session.commit()

    await session.delete(category)

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_deleting_a_tenant_cascades_through_the_whole_catalogue(session, tenant):
    """Categories, products and variants all go with their tenant.

    This is why the product -> category foreign key is NO ACTION rather than
    RESTRICT: RESTRICT is checked immediately and would fire part-way through
    this cascade, depending on the order Postgres happens to delete in.
    """
    category = _category(tenant.id)
    session.add(category)
    await session.commit()
    product = _product(tenant.id, category.id)
    session.add(product)
    await session.commit()
    session.add(_variant(tenant.id, product.id))
    await session.commit()

    await session.delete(tenant)
    await session.commit()

    for model in (Category, Product, ProductVariant):
        assert (await session.execute(select(model))).scalars().all() == []
