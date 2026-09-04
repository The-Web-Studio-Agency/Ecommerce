from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, CurrentUserOptional
from app.core.database import get_db
from app.core.pagination import MAX_PAGE_SIZE, PageParams
from app.core.responses import ApiResponse, ok, paginated
from app.ratings.constants import MAX_RATING, MIN_RATING
from app.search_filter.constants import MAX_QUERY_LENGTH, SearchSort
from app.search_filter.schemas import (
    ProductDiscoveryItem,
    ProductFilters,
    SuggestionItem,
)
from app.search_filter.service import SearchFilterService
from app.tenants.resolver import CurrentTenant

router = APIRouter(prefix="/storefront", tags=["Product Search & Filtering"])


@router.get(
    "/search-products",
    response_model=ApiResponse[list[ProductDiscoveryItem]],
    summary="Search, filter and sort the storefront catalogue",
)
async def search_and_filter_storefront_products(
    tenant: CurrentTenant,
    current_user: CurrentUserOptional,
    q: str | None = Query(
        default=None,
        max_length=MAX_QUERY_LENGTH,
        description="Global search query",
    ),
    category_id: uuid.UUID | None = Query(
        default=None, description="Filter by category UUID"
    ),
    gender: str | None = Query(default=None, description="Filter by gender"),
    brand: str | None = Query(default=None, description="Filter by brand"),
    min_price: Decimal | None = Query(default=None, ge=0, description="Minimum price"),
    max_price: Decimal | None = Query(default=None, ge=0, description="Maximum price"),
    color: str | None = Query(default=None, description="Filter by color"),
    product_size: str | None = Query(
        default=None, description="Filter by product size"
    ),
    min_rating: float | None = Query(
        default=None, ge=MIN_RATING, le=MAX_RATING, description="Minimum rating"
    ),
    max_rating: float | None = Query(
        default=None, ge=MIN_RATING, le=MAX_RATING, description="Maximum rating"
    ),
    sort: SearchSort = Query(
        default=SearchSort.RECOMMENDED, description="Sorting option"
    ),
    page: int = Query(default=1, ge=1, description="1-based page number"),
    size: int = Query(
        default=10,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE})",
    ),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ProductDiscoveryItem]]:
    params = PageParams(page=page, page_size=size)
    filters = ProductFilters(
        search=q,
        category_id=category_id,
        gender=gender,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        color=color,
        size=product_size,
        min_rating=min_rating,
        max_rating=max_rating,
        sort=sort,
    )

    service = SearchFilterService(session, tenant.id)
    products, total = await service.discover(filters, params)

    if current_user is not None:
        await service.record_search(current_user.id, q)

    return paginated(
        products, total_items=total, params=params, message="Products retrieved"
    )


@router.get(
    "/search-suggestions",
    response_model=ApiResponse[list[SuggestionItem]],
    summary="Autocomplete product names, brands and categories",
)
async def get_search_suggestions(
    tenant: CurrentTenant,
    q: str = Query(
        min_length=1,
        max_length=MAX_QUERY_LENGTH,
        description="Autocomplete query string",
    ),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SuggestionItem]]:
    suggestions = await SearchFilterService(session, tenant.id).suggestions(q)
    return ok(suggestions, message="Suggestions retrieved")


@router.get(
    "/search-history",
    response_model=ApiResponse[list[str]],
    summary="The signed-in shopper's recent searches",
)
async def get_recent_searches(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[str]]:
    history = await SearchFilterService(
        session, current_user.tenant_id
    ).recent_searches(current_user.id)
    return ok(history, message="Search history retrieved")
