from __future__ import annotations

from fastapi import APIRouter

from app.addresses.router import router as addresses_router
from app.auth.router import admin_router as auth_admin_router
from app.auth.router import router as auth_router
from app.auth.router import staff_router as auth_staff_router
from app.cart.router import router as cart_router
from app.catalogue.router import router as catalogue_router
from app.catalogue.storefront import router as storefront_router
from app.orders.router import admin_router as orders_admin_router
from app.orders.router import checkout_router
from app.orders.router import router as orders_router
from app.users.router import router as users_router
from app.wishlist.router import router as wishlist_router

api_router = APIRouter()

#authentication
api_router.include_router(auth_router)
api_router.include_router(auth_admin_router)
api_router.include_router(auth_staff_router)
api_router.include_router(users_router)

#catalogue
api_router.include_router(catalogue_router)
api_router.include_router(storefront_router)

#cart
api_router.include_router(cart_router)

#checkout and orders
api_router.include_router(addresses_router)
api_router.include_router(checkout_router)
api_router.include_router(orders_router)
api_router.include_router(orders_admin_router)

