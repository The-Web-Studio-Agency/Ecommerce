from __future__ import annotations

from app.core.repository import TenantScopedRepository
from app.pricing.models import ShippingSettings, TaxSettings


class ShippingSettingsRepository(TenantScopedRepository[ShippingSettings]):
    model = ShippingSettings

    async def get_for_tenant(self) -> ShippingSettings | None:
        """The tenant's one row, if they have configured delivery at all."""
        return await self.session.scalar(self.base_select())


class TaxSettingsRepository(TenantScopedRepository[TaxSettings]):
    model = TaxSettings

    async def get_for_tenant(self) -> TaxSettings | None:
        return await self.session.scalar(self.base_select())
