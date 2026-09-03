from __future__ import annotations

import re
import uuid
from typing import List, Optional, Tuple
from app.catalogue.constants import CatalogueStatus
from app.orders.constants import OrderStatus
from sqlalchemy import select, or_, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalogue.models import Product, ProductVariant, ProductVariantOption, ProductOption, Category
from app.orders.models import Order, OrderItem
from app.ratings.models import Review
from app.search_filter.models import SearchHistory

# A word/number run, extracted after apostrophes are dropped -- so "Women's"
# tokenizes to "Womens", the same as it does on the stored-text side (see
# _token_matches), instead of splitting into an orphan "s" on the apostrophe.
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


def _tokenize(query: str) -> List[str]:
    return _TOKEN_PATTERN.findall(query.replace("'", ""))


class SearchFilterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _has_option(option_name: str, value: str):
        """EXISTS-style predicate: the variant carries a `option_name` option
        (e.g. Color, Size, Gender) set to `value`. Variant option values live
        on ProductVariantOption; the dimension's name lives one hop further,
        on the ProductOption it points at. Both sides are admin-entered free
        text, so matching is case-insensitive ("nike" must match "Nike")."""
        return ProductVariant.option_values.any(
            and_(
                func.lower(ProductVariantOption.value) == value.lower(),
                ProductVariantOption.option.has(func.lower(ProductOption.name) == option_name.lower()),
            )
        )

    @staticmethod
    def _token_matches(token: str):
        """Whether a single search token appears anywhere in one of this
        product's searchable fields -- name, brand, short/long description,
        SKU, or its Gender option value. Apostrophes are stripped from the
        stored text the same way they were stripped from the token, so a
        query token like "Womens" (from "Women's") still matches text that
        actually reads "Women's"."""
        pattern = f"%{token}%"

        def _clean(column):
            return func.replace(column, "'", "")

        return or_(
            _clean(Product.name).ilike(pattern),
            _clean(Product.brand).ilike(pattern),
            _clean(Product.short_description).ilike(pattern),
            _clean(Product.description).ilike(pattern),
            _clean(ProductVariant.sku).ilike(pattern),
            ProductVariant.option_values.any(
                and_(
                    ProductVariantOption.option.has(func.lower(ProductOption.name) == "gender"),
                    _clean(ProductVariantOption.value).ilike(pattern),
                )
            ),
        )

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
    ) -> Tuple[List[Tuple[Product, object, object]], int]:

        # Correlated scalar subqueries rather than extra joins: joining
        # reviews/order_items directly alongside the variants join would
        # cross-multiply rows per product (one row per variant x review x
        # order_item), corrupting anything but MIN/AVG. Scalar subqueries
        # sidestep that entirely and don't need to appear in GROUP BY --
        # Postgres treats them as ordinary expressions, evaluated once per
        # product row.
        avg_rating = (
            select(func.avg(Review.rating))
            .where(
                Review.tenant_id == Product.tenant_id,
                Review.product_id == Product.id,
                Review.is_approved.is_(True),
            )
            .correlate(Product)
            .scalar_subquery()
        )

        popularity = (
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .join(
                Order,
                and_(Order.tenant_id == OrderItem.tenant_id, Order.id == OrderItem.order_id),
            )
            .where(
                OrderItem.tenant_id == Product.tenant_id,
                OrderItem.product_id == Product.id,
                Order.status != OrderStatus.CANCELLED.value,
            )
            .correlate(Product)
            .scalar_subquery()
        )

        stmt = (
            select(
                Product,
                func.min(ProductVariant.price).label("price"),
                avg_rating.label("rating"),
            )
            .join(
                ProductVariant,
                and_(
                    ProductVariant.tenant_id == Product.tenant_id,
                    ProductVariant.product_id == Product.id,
                ),
            )
            .where(
                Product.tenant_id == tenant_id,
                Product.status == CatalogueStatus.ACTIVE.value,
                ProductVariant.status == CatalogueStatus.ACTIVE.value,
            )
        )

        if search:
            # Token/word matching, not one exact-phrase substring: every
            # token in the query must appear SOMEWHERE across the product's
            # searchable fields (not necessarily the same field), so "Women's
            # dress" matches a product named "Women's Maxi Dress" even though
            # that exact phrase never occurs verbatim.
            for token in _tokenize(search):
                stmt = stmt.where(self._token_matches(token))

        if category_id:
            stmt = stmt.where(Product.category_id == category_id)

        if brand:
            stmt = stmt.where(func.lower(Product.brand) == brand.lower())

        if min_price is not None:
            stmt = stmt.where(ProductVariant.price >= min_price)

        if max_price is not None:
            stmt = stmt.where(ProductVariant.price <= max_price)

        if gender:
            stmt = stmt.where(self._has_option("Gender", gender))

        if color:
            stmt = stmt.where(self._has_option("Color", color))

        if size:
            stmt = stmt.where(self._has_option("Size", size))

        # Group by the product's own primary key only: every other Product
        # column, and both correlated scalar subqueries above, are
        # functionally dependent on it, so Postgres allows selecting/
        # filtering on them without listing each one here.
        stmt = stmt.group_by(Product.id)

        if min_rating is not None:
            stmt = stmt.having(avg_rating >= min_rating)

        if max_rating is not None:
            stmt = stmt.having(avg_rating <= max_rating)

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
            # RECOMMENDED (default): most-ordered products first, newest as
            # the tiebreaker for products with equal (often zero) orders.
            stmt = stmt.order_by(desc(popularity), desc(Product.created_at))

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.session.execute(stmt)
        rows = [(product, price, rating) for product, price, rating in result.all()]
        return rows, total

    async def get_variant_attributes(
        self, tenant_id: uuid.UUID, product_ids: List[uuid.UUID]
    ) -> dict[uuid.UUID, List[dict]]:
        """The actual, per-variant option values (Color, Size, ...) for a set
        of products -- straight off ProductVariant/ProductVariantOption, the
        same rows the color/size filters already match against. Only ACTIVE
        variants are included, matching discover_products' own visibility
        rule."""
        if not product_ids:
            return {}

        stmt = (
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.option_values).selectinload(ProductVariantOption.option)
            )
            .where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.product_id.in_(product_ids),
                ProductVariant.status == CatalogueStatus.ACTIVE.value,
            )
            .order_by(ProductVariant.created_at)
        )
        result = await self.session.scalars(stmt)

        attributes: dict[uuid.UUID, List[dict]] = {pid: [] for pid in product_ids}
        for variant in result.all():
            options = {
                option_value.option.name: option_value.value
                for option_value in variant.option_values
            }
            attributes.setdefault(variant.product_id, []).append(
                {"variant_id": variant.id, "options": options}
            )
        return attributes

    async def get_search_suggestions(self, tenant_id: uuid.UUID, query: str) -> List[str]:
        pattern = f"%{query}%"

        # Fetch matching active product names, brands, and categories
        product_names = (
            select(Product.name)
            .where(
                Product.tenant_id == tenant_id,
                Product.status == CatalogueStatus.ACTIVE.value,
                Product.name.ilike(pattern)
            )
            .limit(5)
        )
        brands = (
            select(Product.brand)
            .where(
                Product.tenant_id == tenant_id,
                Product.status == CatalogueStatus.ACTIVE.value,
                Product.brand.ilike(pattern)
            )
            .distinct()
            .limit(5)
        )
        categories = (
            select(Category.name)
            .where(
                Category.tenant_id == tenant_id,
                Category.status == CatalogueStatus.ACTIVE.value,
                Category.name.ilike(pattern)
            )
            .limit(5)
        )

        p_res = await self.session.scalars(product_names)
        b_res = await self.session.scalars(brands)
        c_res = await self.session.scalars(categories)

        suggestions = list(set(list(p_res.all()) + list(b_res.all()) + list(c_res.all())))
        return suggestions[:10]

    async def save_search_history(self, tenant_id: uuid.UUID, user_id: uuid.UUID, query: str):
        if not query.strip():
            return

        history_entry = SearchHistory(tenant_id=tenant_id, user_id=user_id, query=query.strip())
        self.session.add(history_entry)
        await self.session.commit()

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
        seen = set()
        return [q for q in result.all() if not (q in seen or seen.add(q))]
