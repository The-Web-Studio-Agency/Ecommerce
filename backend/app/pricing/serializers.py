"""Turn settings rows into API payloads."""

from __future__ import annotations

from app.core.money import ZERO
from app.pricing.models import ShippingSettings, TaxSettings
from app.pricing.schemas import ShippingSettingsRead, TaxSettingsRead


def shipping_read(settings: ShippingSettings | None) -> ShippingSettingsRead:
    """A tenant that has configured nothing charges nothing."""
    if settings is None:
        return ShippingSettingsRead(
            shipping_amount=ZERO, free_shipping_minimum=None, is_active=False
        )

    return ShippingSettingsRead(
        shipping_amount=settings.shipping_amount,
        free_shipping_minimum=settings.free_shipping_minimum,
        is_active=settings.is_active,
    )


def tax_read(settings: TaxSettings | None) -> TaxSettingsRead:
    if settings is None:
        return TaxSettingsRead(tax_percentage=ZERO, is_active=False)

    return TaxSettingsRead(
        tax_percentage=settings.tax_percentage, is_active=settings.is_active
    )
