from __future__ import annotations

from fastapi import APIRouter

from app.addresses.router import router as addresses_router
from app.auth.router import admin_router as auth_admin_router
from app.auth.router import router as auth_router
from app.auth.router import staff_router as auth_staff_router
from app.cart.router import router as cart_router
from app.catalogue.router import router as catalogue_router
from app.catalogue.storefront import router as storefront_router
from app.core.config import get_settings
from app.coupons.router import admin_router as coupons_admin_router
from app.coupons.router import router as coupons_router
from app.dashboard.router import router as dashboard_router
from app.orders.router import admin_router as orders_admin_router
from app.orders.router import checkout_router
from app.orders.router import router as orders_router
from app.payments.router import admin_router as payments_admin_router
from app.payments.router import router as payments_router
from app.pricing.router import shipping_router, tax_router
from app.ratings.router import admin_router as ratings_admin_router
from app.ratings.router import router as ratings_router
from app.search_filter.router import router as search_filter_router
from app.users.router import router as users_router
from app.wishlist.router import router as wishlist_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(auth_admin_router)
api_router.include_router(auth_staff_router)
api_router.include_router(users_router)

api_router.include_router(catalogue_router)
api_router.include_router(storefront_router)

# TEMPORARY DEV-ONLY -- stand-in for the not-yet-built Admin panel, letting
# any signed-in (non-admin) session populate the catalogue for testing. See
# app/catalogue/dev_router.py for the full removal note; delete that file and
# this block together once Admin ships. Never registered in production, so
# these routes do not exist there regardless of who is signed in.
if not get_settings().is_production:
    from app.catalogue.dev_router import router as dev_catalogue_router

    api_router.include_router(dev_catalogue_router)

api_router.include_router(cart_router)

api_router.include_router(addresses_router)
api_router.include_router(checkout_router)
api_router.include_router(orders_router)
api_router.include_router(orders_admin_router)

api_router.include_router(wishlist_router)

api_router.include_router(payments_router)
api_router.include_router(payments_admin_router)

api_router.include_router(shipping_router)
api_router.include_router(tax_router)

api_router.include_router(coupons_router)
api_router.include_router(coupons_admin_router)
api_router.include_router(ratings_router)
api_router.include_router(ratings_admin_router)

api_router.include_router(search_filter_router)

api_router.include_router(dashboard_router)
