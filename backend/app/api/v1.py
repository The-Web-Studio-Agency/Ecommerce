"""API v1 router aggregation.

Every versioned route is mounted here and the whole tree is included once, under
`settings.api_v1_prefix`. Feature routers therefore declare only their own
prefix (`/auth`), so introducing a v2 is a routing change in one file rather
than an edit to every router.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.catalogue.router import router as catalogue_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(catalogue_router)
