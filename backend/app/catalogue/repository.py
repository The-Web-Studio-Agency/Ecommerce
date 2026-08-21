from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, and_

from app.catalogue.constants import CatalogueStatus
from app.catalogue.models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
)
from app.core.repository import TenantScopedRepository


class CategoryRepository(TenantScopedRepository[Category]):
    model = Category

    def list_select(
        self,
        *,
        active_only: bool = False,
    ) -> Select[tuple[Category]]:
        stmt = self.base_select()

        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))

        return stmt.order_by(Category.name)


class ProductRepository(TenantScopedRepository[Product]):
    model = Product

    def list_select(
        self,
        *,
        category_id: UUID | None = None,
        active_only: bool = False,
    ) -> Select[tuple[Product]]:
        stmt = self.base_select()

        if category_id is not None:
            stmt = stmt.where(
                Product.category_id == category_id
            )

        if active_only:
            # A product is only public when its category is public too,
            # otherwise deactivating a category leaves its products listed.
            stmt = stmt.join(
                Category,
                and_(
                    Category.id == Product.category_id,
                    Category.tenant_id == Product.tenant_id,
                ),
            ).where(
                Product.status == CatalogueStatus.ACTIVE.value,
                Category.is_active.is_(True),
            )

        return stmt.order_by(Product.name)

    async def exists_in_category(
        self,
        category_id: UUID,
    ) -> bool:
        product = await self.find_one(
            Product.category_id == category_id
        )

        return product is not None


class VariantRepository(TenantScopedRepository[ProductVariant]):
    model = ProductVariant

    def list_select(
        self,
        product_id: UUID,
        *,
        active_only: bool = False,
    ) -> Select[tuple[ProductVariant]]:
        stmt = self.base_select().where(
            ProductVariant.product_id == product_id
        )

        if active_only:
            stmt = stmt.where(
                ProductVariant.status == CatalogueStatus.ACTIVE.value
            )

        return stmt.order_by(ProductVariant.sku)

    async def get_by_sku(
        self,
        sku: str,
    ) -> ProductVariant | None:
        return await self.find_one(
            ProductVariant.sku == sku
        )


class ProductImageRepository(
    TenantScopedRepository[ProductImage]
):
    model = ProductImage

    def list_select(
        self,
        product_id: UUID,
    ) -> Select[tuple[ProductImage]]:
        return (
            self.base_select()
            .where(
                ProductImage.product_id == product_id
            )
            .order_by(
                ProductImage.sort_order,
                ProductImage.created_at,
            )
        )

    async def get_primary(
        self,
        product_id: UUID,
    ) -> ProductImage | None:
        return await self.find_one(
            ProductImage.product_id == product_id,
            ProductImage.is_primary.is_(True),
        )