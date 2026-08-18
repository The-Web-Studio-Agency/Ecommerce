from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.constants import OtpPurpose, UserRole, UserStatus
from app.auth.models import OtpRequest, RefreshToken
from app.catalogue.constants import CatalogueStatus
from app.catalogue.models import Category, Product, ProductVariant
from app.tenants.models import Tenant, TenantDomain
from app.users.models import User

PHONE = "+919876543210"


def _user(
    tenant_id,
    phone: str = PHONE,
    role: str = UserRole.CUSTOMER.value,
    email: str | None = None,
    password_hash: str | None = None,
) -> User:
    if role != UserRole.CUSTOMER.value:
        if password_hash is None:
            password_hash = "not-a-real-hash"
        if email is None:
            email = f"staff-{uuid.uuid4().hex[:8]}@example.com"
    return User(
        tenant_id=tenant_id,
        phone=phone,
        email=email,
        role=role,
        password_hash=password_hash,
        status=UserStatus.ACTIVE.value,
    )


async def test_a_phone_is_unique_within_a_tenant(session, tenant):
    session.add(_user(tenant.id))
    await session.commit()

    session.add(_user(tenant.id))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_the_same_phone_is_allowed_across_tenants(session, tenant, other_tenant):
    session.add_all([_user(tenant.id), _user(other_tenant.id)])

    await session.commit()

    rows = (await session.execute(select(User))).scalars().all()
    assert len(rows) == 2


async def test_an_email_is_unique_within_a_tenant(session, tenant):
    session.add(_user(tenant.id, phone="+919000000001", email="dup@example.com"))
    await session.commit()

    session.add(_user(tenant.id, phone="+919000000002", email="dup@example.com"))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_many_customers_may_have_no_email(session, tenant):
    session.add_all(
        [_user(tenant.id, phone="+919000000001"), _user(tenant.id, phone="+919000000002")]
    )

    await session.commit()


async def test_a_tenant_slug_is_unique(session, tenant):
    session.add(Tenant(name="Copy", slug="zeen", is_active=True))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_role_must_be_a_known_value(session, tenant):
    session.add(_user(tenant.id, role="SUPER_DUPER_ADMIN", password_hash="x"))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.parametrize("role", [r.value for r in UserRole])
async def test_every_application_role_is_accepted(session, tenant, role):
    session.add(_user(tenant.id, role=role))

    await session.commit()


async def test_every_user_must_have_a_phone(session, tenant):
    session.add(_user(tenant.id, phone=None))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_an_otp_purpose_must_be_a_known_value(session, tenant):
    session.add(
        OtpRequest(
            tenant_id=tenant.id,
            phone=PHONE,
            purpose="MISCHIEF",
            otp_hash="a-hash",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_status_must_be_a_known_value(session, tenant):
    user = _user(tenant.id)
    user.status = "VIBING"
    session.add(user)

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.parametrize("phone", ["9876543210", "+0123456789", "not-a-phone", "+91"])
async def test_a_phone_must_be_e164(session, tenant, phone):
    session.add(_user(tenant.id, phone=phone))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_an_email_must_be_lowercase(session, tenant):
    session.add(_user(tenant.id, email="Mixed@Example.com"))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_customer_cannot_hold_a_password(session, tenant):
    session.add(_user(tenant.id, role=UserRole.CUSTOMER.value, password_hash="a-hash"))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.parametrize("role", [UserRole.STAFF.value, UserRole.ADMIN.value])
async def test_staff_must_hold_a_password(session, tenant, role):
    user = _user(tenant.id, role=role)
    user.password_hash = None
    session.add(user)

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_user_must_belong_to_a_tenant(session, tenant):
    session.add(_user(None))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_defaults_are_applied(session, tenant):
    user = User(tenant_id=tenant.id, phone=PHONE)
    session.add(user)
    await session.commit()

    assert user.role == UserRole.CUSTOMER.value
    assert user.status == UserStatus.ACTIVE.value
    assert user.is_verified is False
    assert user.created_at is not None


async def test_timestamps_are_server_generated(session, tenant):
    user = _user(tenant.id)
    session.add(user)
    await session.commit()

    assert user.created_at is not None
    assert user.updated_at is not None


async def test_user_ids_are_not_sequential(session, tenant):
    first = _user(tenant.id, phone="+919000000001")
    second = _user(tenant.id, phone="+919000000002")
    session.add_all([first, second])
    await session.commit()

    assert isinstance(first.id, uuid.UUID)
    assert first.id != second.id


async def test_deleting_a_tenant_cascades_to_its_users(session, tenant, other_tenant):
    session.add(_user(tenant.id, phone="+919000000001"))
    session.add(_user(other_tenant.id, phone="+919000000002"))
    await session.commit()

    await session.delete(tenant)
    await session.commit()

    remaining = (await session.execute(select(User))).scalars().all()
    assert [u.phone for u in remaining] == ["+919000000002"]


async def test_deleting_a_user_cascades_to_their_codes_and_sessions(session, tenant):
    user = _user(tenant.id)
    session.add(user)
    await session.commit()

    session.add(
        OtpRequest(
            tenant_id=tenant.id,
            user_id=user.id,
            phone=user.phone,
            purpose=OtpPurpose.CUSTOMER_LOGIN.value,
            otp_hash="a-hash",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    session.add(
        RefreshToken(
            user_id=user.id,
            tenant_id=tenant.id,
            token_hash="a" * 64,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
    )
    await session.commit()

    await session.delete(user)
    await session.commit()

    assert (await session.execute(select(OtpRequest))).scalars().all() == []
    assert (await session.execute(select(RefreshToken))).scalars().all() == []


async def test_an_otp_may_exist_without_a_user(session, tenant):
    session.add(
        OtpRequest(
            tenant_id=tenant.id,
            user_id=None,
            phone=PHONE,
            purpose=OtpPurpose.CUSTOMER_LOGIN.value,
            otp_hash="a-hash",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )

    await session.commit()


async def test_attempts_cannot_go_negative(session, tenant):
    session.add(
        OtpRequest(
            tenant_id=tenant.id,
            phone=PHONE,
            purpose=OtpPurpose.CUSTOMER_LOGIN.value,
            otp_hash="a-hash",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            attempts=-1,
        )
    )

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_domain_serves_only_one_tenant(session, tenant, other_tenant):
    session.add(TenantDomain(tenant_id=other_tenant.id, domain="zeen.test"))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_domain_must_be_lowercase(session, tenant):
    session.add(TenantDomain(tenant_id=tenant.id, domain="Zeen.Test"))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_a_domain_cannot_be_blank(session, tenant):
    session.add(TenantDomain(tenant_id=tenant.id, domain="   "))

    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_deleting_a_tenant_cascades_to_its_domains(session, tenant):
    await session.delete(tenant)
    await session.commit()

    assert (await session.execute(select(TenantDomain))).scalars().all() == []


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

    await session.commit()


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
        ("slug", "Dresses"),
        ("name", "   "),
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
