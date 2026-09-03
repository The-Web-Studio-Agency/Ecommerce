from __future__ import annotations

import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from app.search_filter.repository import SearchFilterRepository
from app.search_filter.schemas import ProductDiscoveryItem, SuggestionItem, VariantAttributes

class SearchFilterService:
    def __init__(self, repo: SearchFilterRepository):
        self.repo = repo

    async def discover_products(
        self,
        tenant_id: uuid.UUID,
        search: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        gender: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        color: Optional[str] = None,
        size: Optional[str] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        sort_by: str = "RECOMMENDED",
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[ProductDiscoveryItem], int]:

        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_price cannot be greater than max_price"
            )

        if min_rating is not None and max_rating is not None and min_rating > max_rating:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_rating cannot be greater than max_rating"
            )

        rows, total = await self.repo.discover_products(
            tenant_id=tenant_id,
            search=search,
            category_id=category_id,
            gender=gender,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            color=color,
            size=size,
            min_rating=min_rating,
            max_rating=max_rating,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )

        variant_attributes = await self.repo.get_variant_attributes(
            tenant_id, [product.id for product, _, _ in rows]
        )

        items = [
            ProductDiscoveryItem(
                id=product.id,
                name=product.name,
                brand=product.brand,
                gender=product.gender,
                category_id=product.category_id,
                price=price,
                min_price=price,
                max_price=price,
                rating=round(rating, 2) if rating is not None else None,
                variants=[
                    VariantAttributes(variant_id=v["variant_id"], options=v["options"])
                    for v in variant_attributes.get(product.id, [])
                ],
            )
            for product, price, rating in rows
        ]
        return items, total

    async def get_suggestions(self, tenant_id: uuid.UUID, query: str) -> List[SuggestionItem]:
        if not query or len(query.strip()) < 1:
            return []
        titles = await self.repo.get_search_suggestions(tenant_id, query)
        return [SuggestionItem(title=title) for title in titles]

    async def record_search(self, tenant_id: uuid.UUID, user_id: uuid.UUID, query: Optional[str]) -> None:
        if query and query.strip():
            await self.repo.save_search_history(tenant_id, user_id, query)

    async def get_history(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> List[str]:
        return await self.repo.get_search_history(tenant_id, user_id)
