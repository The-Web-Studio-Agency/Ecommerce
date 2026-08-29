from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_staff
from app.core.database import get_db
from app.core.responses import ApiResponse, ok
from app.pricing.schemas import (
    ShippingSettingsRead,
    ShippingSettingsUpdate,
    TaxSettingsRead,
    TaxSettingsUpdate,
)
from app.pricing.serializers import shipping_read, tax_read
from app.pricing.service import ShippingService, TaxService
from app.users.models import User

# Store configuration. Staff may read what the shop charges; only an ADMIN may
# change it. The tenant always comes from the access token, never the body.
shipping_router = APIRouter(prefix="/admin/shipping", tags=["Admin-Shipping"])

tax_router = APIRouter(prefix="/admin/tax", tags=["Admin-Tax"])


# ------------------------------- SHIPPING -----------------------------------


@shipping_router.get(
    "",
    response_model=ApiResponse[ShippingSettingsRead],
    summary="View the delivery charge",
)
async def get_shipping_settings(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[ShippingSettingsRead]:
    settings = await ShippingService(session, user.tenant_id).get_settings()
    return ok(shipping_read(settings), message="Shipping settings retrieved")


@shipping_router.put(
    "",
    response_model=ApiResponse[ShippingSettingsRead],
    summary="Set the delivery charge",
)
async def update_shipping_settings(
    data: ShippingSettingsUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[ShippingSettingsRead]:
    settings = await ShippingService(session, user.tenant_id).update_settings(data)
    return ok(shipping_read(settings), message="Shipping settings updated")


# --------------------------------- TAX --------------------------------------


@tax_router.get(
    "",
    response_model=ApiResponse[TaxSettingsRead],
    summary="View the tax rate",
)
async def get_tax_settings(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[TaxSettingsRead]:
    settings = await TaxService(session, user.tenant_id).get_settings()
    return ok(tax_read(settings), message="Tax settings retrieved")


@tax_router.put(
    "",
    response_model=ApiResponse[TaxSettingsRead],
    summary="Set the tax rate",
)
async def update_tax_settings(
    data: TaxSettingsUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[TaxSettingsRead]:
    settings = await TaxService(session, user.tenant_id).update_settings(data)
    return ok(tax_read(settings), message="Tax settings updated")
