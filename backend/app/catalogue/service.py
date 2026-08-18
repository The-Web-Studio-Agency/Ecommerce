from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalogue.models import Category, Product, ProductVariant
from app.catalogue.repository import (
    CategoryRepository,
    ProductRepository,
    VariantRepository,
)
from app.catalogue.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductUpdate,
    VariantCreate,
    VariantUpdate,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.pagination import PageParams

logger = get_logger("catalogue")


def _normalise_slug(slug: str) -> str:
    return slug.strip().lower()


def _normalise_sku(sku: str) -> str:
    return sku.strip().upper()


class CategoryService:
    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.categories = CategoryRepository(session, tenant_id)
        self.products = ProductRepository(session, tenant_id)

    async def create(self, data: CategoryCreate) -> Category:
        slug = _normalise_slug(data.slug)
        if await self.categories.get_by_slug(slug) is not None:
            raise ConflictError("A category with this slug already exists")

        category = Category(
            name=data.name,
            slug=slug,
            description=data.description,
            is_active=data.is_active,
        )
        try:
            await self.categories.add(category)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A category with this slug already exists") from exc

        logger.info("catalogue.category_created id=%s tenant_id=%s", category.id, self.tenant_id)
        return category

    async def get(self, category_id: UUID) -> Category:
        category = await self.categories.get(category_id)
        if category is None:
            raise NotFoundError("Category not found")
        return category

    async def list(self, params: PageParams) -> tuple[list[Category], int]:
        rows, total = await self.categories.paginate(self.categories.list_select(), params)
        return list(rows), total

    async def update(self, category_id: UUID, data: CategoryUpdate) -> Category:
        category = await self.get(category_id)
        changes = data.model_dump(exclude_unset=True)

        if "slug" in changes:
            slug = _normalise_slug(changes["slug"])
            existing = await self.categories.get_by_slug(slug)
            if existing is not None and existing.id != category.id:
                raise ConflictError("A category with this slug already exists")
            changes["slug"] = slug

        for field, value in changes.items():
            setattr(category, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A category with this slug already exists") from exc

        logger.info("catalogue.category_updated id=%s tenant_id=%s", category.id, self.tenant_id)
        return category

    async def delete(self, category_id: UUID) -> None:
        category = await self.get(category_id)
        if await self.products.exists_in_category(category.id):
            raise ConflictError("Category still has products and cannot be deleted")

        await self.categories.delete(category)
        await self.session.commit()
        logger.info("catalogue.category_deleted id=%s tenant_id=%s", category_id, self.tenant_id)


class ProductService:
    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.products = ProductRepository(session, tenant_id)
        self.categories = CategoryRepository(session, tenant_id)

    async def _require_category(self, category_id: UUID) -> Category:
        category = await self.categories.get(category_id)
        if category is None:
            raise NotFoundError("Category not found")
        return category

    async def create(self, data: ProductCreate) -> Product:
        await self._require_category(data.category_id)

        slug = _normalise_slug(data.slug)
        if await self.products.get_by_slug(slug) is not None:
            raise ConflictError("A product with this slug already exists")

        product = Product(
            category_id=data.category_id,
            name=data.name,
            slug=slug,
            description=data.description,
            status=data.status.value,
        )
        try:
            await self.products.add(product)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A product with this slug already exists") from exc

        logger.info("catalogue.product_created id=%s tenant_id=%s", product.id, self.tenant_id)
        return product

    async def get(self, product_id: UUID) -> Product:
        product = await self.products.get(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return product

    async def list(
        self, params: PageParams, *, category_id: UUID | None = None
    ) -> tuple[list[Product], int]:
        if category_id is not None:
            await self._require_category(category_id)

        rows, total = await self.products.paginate(
            self.products.list_select(category_id=category_id), params
        )
        return list(rows), total

    async def update(self, product_id: UUID, data: ProductUpdate) -> Product:
        product = await self.get(product_id)
        changes = data.model_dump(exclude_unset=True)

        if "category_id" in changes:
            await self._require_category(changes["category_id"])

        if "slug" in changes:
            slug = _normalise_slug(changes["slug"])
            existing = await self.products.get_by_slug(slug)
            if existing is not None and existing.id != product.id:
                raise ConflictError("A product with this slug already exists")
            changes["slug"] = slug

        if "status" in changes and changes["status"] is not None:
            changes["status"] = changes["status"].value

        for field, value in changes.items():
            setattr(product, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A product with this slug already exists") from exc

        logger.info("catalogue.product_updated id=%s tenant_id=%s", product.id, self.tenant_id)
        return product

    async def delete(self, product_id: UUID) -> None:
        product = await self.get(product_id)
        await self.products.delete(product)
        await self.session.commit()
        logger.info("catalogue.product_deleted id=%s tenant_id=%s", product_id, self.tenant_id)


class VariantService:
    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.variants = VariantRepository(session, tenant_id)
        self.products = ProductRepository(session, tenant_id)

    async def _require_product(self, product_id: UUID) -> Product:
        product = await self.products.get(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return product

    async def create(self, product_id: UUID, data: VariantCreate) -> ProductVariant:
        await self._require_product(product_id)

        sku = _normalise_sku(data.sku)
        if await self.variants.get_by_sku(sku) is not None:
            raise ConflictError("A variant with this SKU already exists")

        variant = ProductVariant(
            product_id=product_id,
            sku=sku,
            name=data.name,
            price=data.price,
            status=data.status.value,
        )
        try:
            await self.variants.add(variant)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A variant with this SKU already exists") from exc

        logger.info("catalogue.variant_created id=%s tenant_id=%s", variant.id, self.tenant_id)
        return variant

    async def get(self, variant_id: UUID) -> ProductVariant:
        variant = await self.variants.get(variant_id)
        if variant is None:
            raise NotFoundError("Variant not found")
        return variant

    async def list_for_product(
        self, product_id: UUID, params: PageParams
    ) -> tuple[list[ProductVariant], int]:
        await self._require_product(product_id)
        rows, total = await self.variants.paginate(self.variants.list_select(product_id), params)
        return list(rows), total

    async def update(self, variant_id: UUID, data: VariantUpdate) -> ProductVariant:
        variant = await self.get(variant_id)
        changes = data.model_dump(exclude_unset=True)

        if "sku" in changes:
            sku = _normalise_sku(changes["sku"])
            existing = await self.variants.get_by_sku(sku)
            if existing is not None and existing.id != variant.id:
                raise ConflictError("A variant with this SKU already exists")
            changes["sku"] = sku

        if "status" in changes and changes["status"] is not None:
            changes["status"] = changes["status"].value

        for field, value in changes.items():
            setattr(variant, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A variant with this SKU already exists") from exc

        logger.info("catalogue.variant_updated id=%s tenant_id=%s", variant.id, self.tenant_id)
        return variant

    async def delete(self, variant_id: UUID) -> None:
        variant = await self.get(variant_id)
        await self.variants.delete(variant)
        await self.session.commit()
        logger.info("catalogue.variant_deleted id=%s tenant_id=%s", variant_id, self.tenant_id)
