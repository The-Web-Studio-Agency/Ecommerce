from __future__ import annotations

import uuid
from typing import List, Optional, Tuple
from app.catalogue.constants import CatalogueStatus
from sqlalchemy import select, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalogue.models import Product, ProductVariant, Category
from app.search_filter.models import SearchHistory

class SearchFilterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

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
    ) -> Tuple[List[Tuple[Product, object]], int]:

        stmt = (
            select(Product, func.min(ProductVariant.price).label("price"))
            .join(ProductVariant)
            .where(Product.tenant_id == tenant_id, Product.status == CatalogueStatus.ACTIVE.value)
        )

        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.brand.ilike(search_pattern),
                    ProductVariant.sku.ilike(search_pattern)
                )
            )

        if category_id:
            stmt = stmt.where(Product.category_id == category_id)

        if gender:
            stmt = stmt.where(Product.gender == gender)

        if brand:
            stmt = stmt.where(Product.brand == brand)

        if min_price is not None:
            stmt = stmt.where(ProductVariant.price >= min_price)

        if max_price is not None:
            stmt = stmt.where(ProductVariant.price <= max_price)

        if color:
            stmt = stmt.where(ProductVariant.options.any(name="Color", value=color))

        if size:
            stmt = stmt.where(ProductVariant.options.any(name="Size", value=size))

        # Group by product to avoid duplicate listings per variant match
        stmt = stmt.group_by(Product.id)

        # Counting total matches
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0

        # Sorting
        if sort_by == "PRICE_HIGH":
            stmt = stmt.order_by(desc(func.max(ProductVariant.price)))
        elif sort_by == "PRICE_LOW":
            stmt = stmt.order_by(func.min(ProductVariant.price))
        elif sort_by == "NEWEST":
            stmt = stmt.order_by(desc(Product.created_at))
        else:
            stmt = stmt.order_by(desc(Product.created_at)) # Default RECOMMENDED

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.session.execute(stmt)
        rows = [(product, price) for product, price in result.all()]
        return rows, total

    async def get_search_suggestions(self, tenant_id: uuid.UUID, query: str) -> List[str]:
        pattern = f"%{query}%"
        
        # Fetch matching product names, brands, and categories
        product_names = select(Product.name).where(Product.tenant_id == tenant_id, Product.name.ilike(pattern)).limit(5)
        brands = select(Product.brand).where(Product.tenant_id == tenant_id, Product.brand.ilike(pattern)).distinct().limit(5)
        categories = select(Category.name).where(Category.tenant_id == tenant_id, Category.name.ilike(pattern)).limit(5)

        p_res = await self.session.scalars(product_names)
        b_res = await self.session.scalars(brands)
        c_res = await self.session.scalars(categories)

        suggestions = list(set(list(p_res.all()) + list(b_res.all()) + list(c_res.all())))
        return suggestions[:10]

    async def save_search_history(self, tenant_id: uuid.UUID, user_id: uuid.UUID, query: str):
        if not query.strip():
            return
        
        # Check if already exists recently to avoid duplicates, or just insert and maintain limit
        history_entry = SearchHistory(tenant_id=tenant_id, user_id=user_id, query=query.strip())
        self.session.add(history_entry)
        await self.session.commit()

        # Maintain max 10 recent searches per user
        subquery = (
            select(SearchHistory.id)
            .where(SearchHistory.tenant_id == tenant_id, SearchHistory.user_id == user_id)
            .order_by(desc(SearchHistory.created_at))
            .offset(10)
        )
        old_entries = await self.session.scalars(subquery)
        for old_id in old_entries.all():
            old_obj = await self.session.get(SearchHistory, old_id)
            if old_obj:
                await self.session.delete(old_obj)
        await self.session.commit()

    async def get_search_history(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> List[str]:
        stmt = (
            select(SearchHistory.query)
            .where(SearchHistory.tenant_id == tenant_id, SearchHistory.user_id == user_id)
            .order_by(desc(SearchHistory.created_at))
            .limit(10)
        )
        result = await self.session.scalars(stmt)
        # return unique ordered list
        seen = set()
        return [q for q in result.all() if not (q in seen or seen.add(q))]