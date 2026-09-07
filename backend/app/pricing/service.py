from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.core.logging import get_logger
from app.core.money import ZERO, money
from app.pricing.constants import PERCENT
from app.pricing.models import ShippingSettings, TaxSettings
from app.pricing.repository import ShippingSettingsRepository, TaxSettingsRepository
from app.pricing.schemas import ShippingSettingsUpdate, TaxSettingsUpdate

logger = get_logger("pricing")

SAVE_FAILED = "Unable to save the settings, please try again"


class ShippingService:
    """One flat delivery charge per tenant, optionally free above a threshold."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.settings = ShippingSettingsRepository(session, tenant_id)

    async def get_settings(self) -> ShippingSettings | None:
        return await self.settings.get_for_tenant()

    async def update_settings(self, data: ShippingSettingsUpdate) -> ShippingSettings:
        """Write the tenant's one row, creating it the first time."""
        settings = await self.get_settings()

        try:
            if settings is None:
                settings = ShippingSettings(
                    shipping_amount=data.shipping_amount,
                    free_shipping_minimum=data.free_shipping_minimum,
                    is_active=data.is_active,
                )
                await self.settings.add(settings)
            else:
                settings.shipping_amount = data.shipping_amount
                settings.free_shipping_minimum = data.free_shipping_minimum
                settings.is_active = data.is_active

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(SAVE_FAILED) from exc

        logger.info(
            "pricing.shipping_updated tenant_id=%s amount=%s free_over=%s active=%s",
            self.tenant_id,
            settings.shipping_amount,
            settings.free_shipping_minimum,
            settings.is_active,
        )
        return settings

    async def calculate(self, subtotal: Decimal) -> Decimal:
        """What this basket costs to deliver."""
        settings = await self.get_settings()

        if settings is None or not settings.is_active:
            return ZERO

        minimum = settings.free_shipping_minimum
        if minimum is not None and subtotal >= minimum:
            return ZERO

        return money(settings.shipping_amount)


class TaxService:
    """One tax percentage per tenant, charged on the goods and the delivery."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.settings = TaxSettingsRepository(session, tenant_id)

    async def get_settings(self) -> TaxSettings | None:
        return await self.settings.get_for_tenant()

    async def update_settings(self, data: TaxSettingsUpdate) -> TaxSettings:
        """Write the tenant's one row, creating it the first time."""
        settings = await self.get_settings()

        try:
            if settings is None:
                settings = TaxSettings(
                    tax_percentage=data.tax_percentage, is_active=data.is_active
                )
                await self.settings.add(settings)
            else:
                settings.tax_percentage = data.tax_percentage
                settings.is_active = data.is_active

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(SAVE_FAILED) from exc

        logger.info(
            "pricing.tax_updated tenant_id=%s percentage=%s active=%s",
            self.tenant_id,
            settings.tax_percentage,
            settings.is_active,
        )
        return settings

    async def calculate(self, subtotal: Decimal, shipping: Decimal) -> Decimal:
        """Tax on the goods and the delivery together."""
        settings = await self.get_settings()

        if settings is None or not settings.is_active:
            return ZERO

        taxable = subtotal + shipping
        return money(taxable * settings.tax_percentage / PERCENT)
