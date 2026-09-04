from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, and_, exists, func, or_, select, update

from app.catalogue.constants import CatalogueStatus, ProductSort
from app.catalogue.models import (
    Category,
    InventoryItem,
    Product,
    ProductImage,
    ProductOption,
    ProductVariant,
    ProductVariantOption,
)
from app.core.repository import TenantScopedRepository, escape_like


class CategoryRepository(TenantScopedRepository[Category]):
    model = Category

    def list_select(self, *, active_only: bool = False) -> Select[tuple[Category]]:
        stmt = self.base_select()

        if active_only:
            stmt = stmt.where(Category.status == CatalogueStatus.ACTIVE.value)
        else:
            stmt = stmt.where(Category.status != CatalogueStatus.ARCHIVED.value)

        return stmt.order_by(Category.name)


class ProductRepository(TenantScopedRepository[Product]):
    model = Product

    def _live_price_subquery(self):
        """Cheapest sellable variant price for the product, used for price sorting."""
        return (
            select(func.min(ProductVariant.price))
            .where(
                ProductVariant.tenant_id == Product.tenant_id,
                ProductVariant.product_id == Product.id,
                ProductVariant.status == CatalogueStatus.ACTIVE.value,
            )
            .correlate(Product)
            .scalar_subquery()
        )

    def list_select(
        self,
        *,
        category_id: UUID | None = None,
        search: str | None = None,
        brand: str | None = None,
        featured: bool | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        sort: ProductSort = ProductSort.NAME_ASC,
        active_only: bool = False,
    ) -> Select[tuple[Product]]:
        stmt = self.base_select()

        if active_only:
            stmt = stmt.join(
                Category,
                and_(
                    Category.id == Product.category_id,
                    Category.tenant_id == Product.tenant_id,
                ),
            ).where(
                Product.status == CatalogueStatus.ACTIVE.value,
                Category.status == CatalogueStatus.ACTIVE.value,
            )
        else:
            stmt = stmt.where(Product.status != CatalogueStatus.ARCHIVED.value)

        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)

        if search:
            pattern = f"%{escape_like(search.strip())}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(pattern, escape="\\"),
                    Product.brand.ilike(pattern, escape="\\"),
                )
            )

        if brand:
            stmt = stmt.where(Product.brand == brand.strip())

        if featured is not None:
            stmt = stmt.where(Product.is_featured.is_(featured))

        if min_price is not None or max_price is not None:
            conditions = [
                ProductVariant.tenant_id == Product.tenant_id,
                ProductVariant.product_id == Product.id,
                ProductVariant.status == CatalogueStatus.ACTIVE.value,
            ]
            if min_price is not None:
                conditions.append(ProductVariant.price >= min_price)
            if max_price is not None:
                conditions.append(ProductVariant.price <= max_price)
            stmt = stmt.where(exists().where(and_(*conditions)))

        return stmt.order_by(*self._order_by(sort))

    def _order_by(self, sort: ProductSort):
        price = self._live_price_subquery()
        clauses = {
            ProductSort.NEWEST: (Product.created_at.desc(), Product.id),
            ProductSort.NAME_ASC: (Product.name.asc(), Product.id),
            ProductSort.NAME_DESC: (Product.name.desc(), Product.id),
            ProductSort.PRICE_LOW: (price.asc().nulls_last(), Product.id),
            ProductSort.PRICE_HIGH: (price.desc().nulls_last(), Product.id),
        }
        return clauses[sort]

    async def has_products_in_category(
        self, category_id: UUID, *, include_archived: bool = False
    ) -> bool:
        """Whether the category still holds products, archived ones excluded."""
        conditions = [Product.category_id == category_id]
        if not include_archived:
            conditions.append(Product.status != CatalogueStatus.ARCHIVED.value)

        return await self.find_one(*conditions) is not None

    async def lock(self, product_id: UUID) -> UUID | None:
        """Take a row lock on the product, serialising mutations to its image set."""
        return await self.session.scalar(
            select(Product.id)
            .where(Product.tenant_id == self.tenant_id, Product.id == product_id)
            .with_for_update()
        )


class VariantRepository(TenantScopedRepository[ProductVariant]):
    model = ProductVariant

    def list_select(
        self, product_id: UUID, *, active_only: bool = False
    ) -> Select[tuple[ProductVariant]]:
        stmt = self.base_select().where(ProductVariant.product_id == product_id)

        if active_only:
            stmt = stmt.where(ProductVariant.status == CatalogueStatus.ACTIVE.value)

        return stmt.order_by(ProductVariant.sku)

    async def get_by_sku(self, sku: str) -> ProductVariant | None:
        return await self.find_one(ProductVariant.sku == sku)


class ProductOptionRepository(TenantScopedRepository[ProductOption]):
    model = ProductOption

    def list_select(self, product_id: UUID) -> Select[tuple[ProductOption]]:
        return (
            self.base_select()
            .where(ProductOption.product_id == product_id)
            .order_by(ProductOption.position, ProductOption.name)
        )

    async def get_by_name(self, product_id: UUID, name: str) -> ProductOption | None:
        return await self.find_one(
            ProductOption.product_id == product_id, ProductOption.name == name
        )


class VariantOptionRepository(TenantScopedRepository[ProductVariantOption]):
    model = ProductVariantOption

    async def clear_for_variant(self, variant_id: UUID) -> None:
        await self.session.execute(
            ProductVariantOption.__table__.delete().where(
                ProductVariantOption.tenant_id == self.tenant_id,
                ProductVariantOption.variant_id == variant_id,
            )
        )
        await self.session.flush()


class ProductImageRepository(TenantScopedRepository[ProductImage]):
    model = ProductImage

    def list_select(self, product_id: UUID) -> Select[tuple[ProductImage]]:
        return (
            self.base_select()
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order, ProductImage.created_at)
        )

    async def count_for_product(self, product_id: UUID) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(ProductImage)
            .where(
                ProductImage.tenant_id == self.tenant_id,
                ProductImage.product_id == product_id,
            )
        )
        return int(total or 0)

    async def clear_primary(
        self, product_id: UUID, *, exclude_id: UUID | None = None
    ) -> None:
        """Demote the product's current primary image in a single UPDATE."""
        conditions = [
            ProductImage.tenant_id == self.tenant_id,
            ProductImage.product_id == product_id,
            ProductImage.is_primary.is_(True),
        ]
        if exclude_id is not None:
            conditions.append(ProductImage.id != exclude_id)

        await self.session.execute(
            update(ProductImage).where(*conditions).values(is_primary=False)
        )
        await self.session.flush()


class InventoryRepository(TenantScopedRepository[InventoryItem]):
    """Stock changes as conditional UPDATEs; a rowcount of 0 means it was refused."""

    model = InventoryItem

    async def get_for_variant(self, variant_id: UUID) -> InventoryItem | None:
        return await self.find_one(InventoryItem.variant_id == variant_id)

    async def _apply(self, variant_id: UUID, *conditions, **values) -> bool:
        result = await self.session.execute(
            update(InventoryItem)
            .where(
                InventoryItem.tenant_id == self.tenant_id,
                InventoryItem.variant_id == variant_id,
                *conditions,
            )
            .values(**values)
        )
        await self.session.flush()
        return (result.rowcount or 0) == 1

    async def set_available(self, variant_id: UUID, quantity: int) -> bool:
        return await self._apply(
            variant_id,
            InventoryItem.reserved_quantity <= quantity,
            available_quantity=quantity,
        )

    async def adjust_available(self, variant_id: UUID, delta: int) -> bool:
        return await self._apply(
            variant_id,
            InventoryItem.available_quantity + delta >= InventoryItem.reserved_quantity,
            InventoryItem.available_quantity + delta >= 0,
            available_quantity=InventoryItem.available_quantity + delta,
        )

    async def reserve(self, variant_id: UUID, quantity: int) -> bool:
        return await self._apply(
            variant_id,
            InventoryItem.available_quantity - InventoryItem.reserved_quantity >= quantity,
            reserved_quantity=InventoryItem.reserved_quantity + quantity,
        )

    async def release(self, variant_id: UUID, quantity: int) -> bool:
        return await self._apply(
            variant_id,
            InventoryItem.reserved_quantity >= quantity,
            reserved_quantity=InventoryItem.reserved_quantity - quantity,
        )

    async def fulfil(self, variant_id: UUID, quantity: int) -> bool:
        """Ship reserved stock: it leaves the shelf and the reservation ends."""
        return await self._apply(
            variant_id,
            InventoryItem.reserved_quantity >= quantity,
            InventoryItem.available_quantity >= quantity,
            available_quantity=InventoryItem.available_quantity - quantity,
            reserved_quantity=InventoryItem.reserved_quantity - quantity,
        )

    async def set_threshold(self, variant_id: UUID, threshold: int) -> bool:
        return await self._apply(variant_id, low_stock_threshold=threshold)
