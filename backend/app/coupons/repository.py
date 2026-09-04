from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func

from app.core.repository import TenantScopedRepository
from app.coupons.models import Coupon, CouponUsage


class CouponRepository(TenantScopedRepository[Coupon]):
    model = Coupon

    def list_select(self, *, active_only: bool = False) -> Select[tuple[Coupon]]:
        stmt = self.base_select()
        if active_only:
            stmt = stmt.where(Coupon.is_active == True)
        return stmt.order_by(Coupon.created_at.desc())

    async def get_by_code(self, code: str) -> Coupon | None:
        return await self.find_one(func.upper(Coupon.code) == code.upper())

    async def get_by_code_for_update(self, code: str) -> Coupon | None:
        stmt = self.base_select().where(func.upper(Coupon.code) == code.upper()).with_for_update()
        return await self.session.scalar(stmt)


class CouponUsageRepository(TenantScopedRepository[CouponUsage]):
    model = CouponUsage

    async def count_for_customer(self, coupon_id: UUID, customer_id: UUID) -> int:
        stmt = self.base_select().where(
            CouponUsage.coupon_id == coupon_id,
            CouponUsage.customer_id == customer_id,
        )
        result = await self.session.scalars(stmt)
        return len(result.all())