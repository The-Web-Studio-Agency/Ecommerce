"""Catalogue data access. Queries only - no business rules, no commits.

All three extend `TenantScopedRepository`, so every read below already starts
from a tenant-filtered SELECT and every write is stamped with the tenant. None
of these methods mentions `tenant_id`: that is the point of the base class.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select

from app.catalogue.models import Category, Product, ProductVariant
from app.core.repository import TenantScopedRepository


class CategoryRepository(TenantScopedRepository[Category]):
    model = Category

    def list_select(self) -> Select[tuple[Category]]:
        return self.base_select().order_by(Category.name)

    async def get_by_slug(self, slug: str) -> Category | None:
        return await self.find_one(Category.slug == slug)


class ProductRepository(TenantScopedRepository[Product]):
    model = Product

    def list_select(self, *, category_id: UUID | None = None) -> Select[tuple[Product]]:
        stmt = self.base_select().order_by(Product.name)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        return stmt

    async def get_by_slug(self, slug: str) -> Product | None:
        return await self.find_one(Product.slug == slug)

    async def exists_in_category(self, category_id: UUID) -> bool:
        """Whether a category still has products, so deleting it is refused."""
        product = await self.find_one(Product.category_id == category_id)
        return product is not None


class VariantRepository(TenantScopedRepository[ProductVariant]):
    model = ProductVariant

    def list_select(self, product_id: UUID) -> Select[tuple[ProductVariant]]:
        return (
            self.base_select()
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.sku)
        )

    async def get_by_sku(self, sku: str) -> ProductVariant | None:
        return await self.find_one(ProductVariant.sku == sku)
