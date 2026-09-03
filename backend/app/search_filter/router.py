from __future__ import annotations

import uuid
from typing import Literal, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.tenants.resolver import CurrentTenant
from app.auth.dependencies import CurrentUser
from app.search_filter.repository import SearchFilterRepository
from app.search_filter.service import SearchFilterService
from app.search_filter.schemas import (
    PaginatedDiscoveryResponse,
    ProductDiscoveryItem,
    SearchSuggestionsResponse,
    SearchHistoryResponse,
    SuggestionItem,
)
from app.core.responses import ApiResponse, ok, paginated
from app.core.pagination import PageParams

router = APIRouter(prefix="/storefront", tags=["Product Search & Filtering"])

def get_search_filter_service(session: AsyncSession = Depends(get_db)) -> SearchFilterService:
    repo = SearchFilterRepository(session)
    return SearchFilterService(repo)

_SORT_ALIASES = {
    "-price": "PRICE_HIGH",
    "price": "PRICE_LOW",
}

# Only these tokens are accepted -- anything else is a 422, not a silent
# fallback to RECOMMENDED.
SortOption = Literal["RECOMMENDED", "NEWEST", "price", "-price"]

@router.get("/search-products", response_model=ApiResponse[list[ProductDiscoveryItem]])
async def search_and_filter_storefront_products(
    tenant: CurrentTenant,
    current_user: CurrentUser,
    q: Optional[str] = Query(None, description="Global search query"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category UUID"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    color: Optional[str] = Query(None, description="Filter by color"),
    # A distinct query key from the page-size "size" param below -- the two
    # used to share the name "size" via alias, so ?size=N was silently
    # (mis)read as both a page-size AND a product-size filter at once.
    product_size: Optional[str] = Query(None, description="Filter by product size"),
    min_rating: Optional[float] = Query(None, ge=1, le=5, description="Minimum rating"),
    max_rating: Optional[float] = Query(None, ge=1, le=5, description="Maximum rating"),
    sort: SortOption = Query("RECOMMENDED", description="Sorting option (RECOMMENDED, NEWEST, price, -price)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size limit"),
    service: SearchFilterService = Depends(get_search_filter_service)
):
    sort_by = _SORT_ALIASES.get(sort, sort)
    products, total = await service.discover_products(
        tenant_id=tenant.id,
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
        sort_by=sort_by,
        page=page,
        page_size=size,
    )

    await service.record_search(tenant.id, current_user.id, q)

    return paginated(
        items=products,
        total_items=total,
        params=PageParams(page=page, page_size=size)
    )

@router.get("/search-suggestions", response_model=ApiResponse[list[SuggestionItem]])
async def get_search_suggestions(
    tenant: CurrentTenant,
    q: str = Query(..., min_length=1, description="Autocomplete query string"),
    service: SearchFilterService = Depends(get_search_filter_service)
):
    suggestions = await service.get_suggestions(tenant.id, q)
    return ok(suggestions)

@router.get("/search-history", response_model=ApiResponse[list])
async def get_recent_searches(
    tenant: CurrentTenant,
    current_user: CurrentUser,
    service: SearchFilterService = Depends(get_search_filter_service)
):
    history = await service.get_history(tenant.id, current_user.id)
    return ok(history)
