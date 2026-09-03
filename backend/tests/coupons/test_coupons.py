from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.coupons.models import Coupon
from app.coupons.repository import CouponRepository


@pytest.mark.asyncio
async def test_admin_create_coupon(client: AsyncClient, admin_headers: dict, tenant):
    response = await client.post(
        "/api/v1/admin/coupons",
        json={
            "code": "SAVE20",
            "discount_type": "PERCENTAGE",
            "discount_value": "20.00",
            "min_order_amount": "100.00",
            "max_discount_amount": "50.00",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == "SAVE20"
    assert data["discount_type"] == "PERCENTAGE"
    assert Decimal(data["discount_value"]) == Decimal("20.00")
    assert Decimal(data["min_order_amount"]) == Decimal("100.00")
    assert Decimal(data["max_discount_amount"]) == Decimal("50.00")
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_admin_create_fixed_coupon(client: AsyncClient, admin_headers: dict, tenant):
    response = await client.post(
        "/api/v1/admin/coupons",
        json={
            "code": "FLAT100",
            "discount_type": "FIXED_AMOUNT",
            "discount_value": "100.00",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == "FLAT100"
    assert data["discount_type"] == "FIXED_AMOUNT"
    assert Decimal(data["discount_value"]) == Decimal("100.00")


@pytest.mark.asyncio
async def test_admin_list_coupons(client: AsyncClient, staff_headers: dict, session: AsyncSession, tenant):
    repo = CouponRepository(session, tenant.id)
    coupon = Coupon(
        tenant_id=tenant.id,
        code="LISTME",
        discount_type="FIXED_AMOUNT",
        discount_value=Decimal("50.00"),
        is_active=True,
    )
    await repo.add(coupon)
    await session.commit()

    response = await client.get("/api/v1/admin/coupons", headers=staff_headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["meta"]["total_items"] >= 1
    codes = [item["code"] for item in res_data["data"]]
    assert "LISTME" in codes


@pytest.mark.asyncio
async def test_customer_apply_coupon_success(client: AsyncClient, customer_headers: dict, session: AsyncSession, tenant):
    repo = CouponRepository(session, tenant.id)
    coupon = Coupon(
        tenant_id=tenant.id,
        code="PROMO10",
        discount_type="FIXED_AMOUNT",
        discount_value=Decimal("50.00"),
        min_order_amount=Decimal("200.00"),
        is_active=True,
    )
    await repo.add(coupon)
    await session.commit()

    response = await client.post(
        "/api/v1/coupons/apply",
        json={"code": "promo10"},
        params={"subtotal": "300.00"},
        headers=customer_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == "PROMO10"
    assert Decimal(data["discount_amount"]) == Decimal("50.00")


@pytest.mark.asyncio
async def test_customer_apply_coupon_min_order_fail(client: AsyncClient, customer_headers: dict, session: AsyncSession, tenant):
    repo = CouponRepository(session, tenant.id)
    coupon = Coupon(
        tenant_id=tenant.id,
        code="MINORDER",
        discount_type="FIXED_AMOUNT",
        discount_value=Decimal("50.00"),
        min_order_amount=Decimal("500.00"),
        is_active=True,
    )
    await repo.add(coupon)
    await session.commit()

    response = await client.post(
        "/api/v1/coupons/apply",
        json={"code": "MINORDER"},
        params={"subtotal": "300.00"},
        headers=customer_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_customer_apply_expired_coupon(client: AsyncClient, customer_headers: dict, session: AsyncSession, tenant):
    past_time = datetime.now(timezone.utc) - timedelta(days=2)
    repo = CouponRepository(session, tenant.id)
    coupon = Coupon(
        tenant_id=tenant.id,
        code="EXPIRED",
        discount_type="FIXED_AMOUNT",
        discount_value=Decimal("50.00"),
        expires_at=past_time,
        is_active=True,
    )
    await repo.add(coupon)
    await session.commit()

    response = await client.post(
        "/api/v1/coupons/apply",
        json={"code": "EXPIRED"},
        params={"subtotal": "300.00"},
        headers=customer_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_percentage_coupon_with_max_cap(client: AsyncClient, customer_headers: dict, session: AsyncSession, tenant):
    repo = CouponRepository(session, tenant.id)
    coupon = Coupon(
        tenant_id=tenant.id,
        code="BIGSALE",
        discount_type="PERCENTAGE",
        discount_value=Decimal("50.00"),  # 50% off
        max_discount_amount=Decimal("75.00"),  # Capped at 75
        is_active=True,
    )
    await repo.add(coupon)
    await session.commit()

    # Subtotal 300 -> 50% is 150, but cap is 75
    response = await client.post(
        "/api/v1/coupons/apply",
        json={"code": "BIGSALE"},
        params={"subtotal": "300.00"},
        headers=customer_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert Decimal(data["discount_amount"]) == Decimal("75.00")
