from __future__ import annotations

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalogue.constants import CatalogueStatus
from app.catalogue.models import Category, Product, ProductImage, ProductVariant
from app.catalogue.repository import (
    CategoryRepository,
    ProductImageRepository,
    ProductRepository,
    VariantRepository,
)
from app.catalogue.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductImageCreate,
    ProductImageUpdate,
    ProductUpdate,
    VariantCreate,
    VariantUpdate,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.pagination import PageParams

logger = get_logger("catalogue")


def _normalise_sku(sku: str) -> str:
    return sku.strip().upper()


class CategoryService:
    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

        self.categories = CategoryRepository(session, tenant_id)
        self.products = ProductRepository(session, tenant_id)

    async def create(self, data: CategoryCreate) -> Category:
        category = Category(
            name=data.name,
            description=data.description,
            is_active=data.is_active,
        )

        try:
            await self.categories.add(category)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to create category") from exc

        logger.info(
            "catalogue.category_created id=%s tenant_id=%s",
            category.id,
            self.tenant_id,
        )

        return category

    async def get(self, category_id: UUID) -> Category:
        category = await self.categories.get(category_id)

        if category is None:
            raise NotFoundError("Category not found")

        return category

    async def list(
        self,
        params: PageParams,
        *,
        active_only: bool = False,
    ) -> tuple[list[Category], int]:
        """
        List categories for the tenant.

        active_only=True is intended for public/storefront usage.
        """
        stmt = self.categories.list_select(
            active_only=active_only,
        )

        rows, total = await self.categories.paginate(
            stmt,
            params,
        )

        return list(rows), total

    async def update(
        self,
        category_id: UUID,
        data: CategoryUpdate,
    ) -> Category:
        category = await self.get(category_id)

        changes = data.model_dump(exclude_unset=True)

        for field, value in changes.items():
            setattr(category, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to update category") from exc

        logger.info(
            "catalogue.category_updated id=%s tenant_id=%s",
            category.id,
            self.tenant_id,
        )

        return category

    async def delete(self, category_id: UUID) -> None:
        category = await self.get(category_id)

        if await self.products.exists_in_category(category.id):
            raise ConflictError(
                "Category still has products and cannot be deleted"
            )

        await self.categories.delete(category)
        await self.session.commit()

        logger.info(
            "catalogue.category_deleted id=%s tenant_id=%s",
            category_id,
            self.tenant_id,
        )


class ProductService:
    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

        self.products = ProductRepository(session, tenant_id)
        self.categories = CategoryRepository(session, tenant_id)
        self.images = ProductImageRepository(session, tenant_id)

    async def _require_category(self, category_id: UUID) -> Category:
        category = await self.categories.get(category_id)

        if category is None:
            raise NotFoundError("Category not found")

        return category

    async def create(self, data: ProductCreate) -> Product:
        """
        Create a product together with its images in one transaction.

        A product is not publishable without artwork, so the schema requires at
        least one image and both rows are written atomically -- a product never
        exists in an image-less state.
        """
        await self._require_category(data.category_id)

        product = Product(
            category_id=data.category_id,
            name=data.name,
            short_description=data.short_description,
            description=data.description,
            brand=data.brand,
            status=data.status.value,
            is_featured=data.is_featured,
            seo_title=data.seo_title,
            seo_description=data.seo_description,
        )

        try:
            await self.products.add(product)

            # If the caller nominated no primary, the first image becomes one.
            has_primary = any(image.is_primary for image in data.images)

            for position, image in enumerate(data.images):
                await self.images.add(
                    ProductImage(
                        product_id=product.id,
                        url=image.url,
                        alt_text=image.alt_text,
                        sort_order=image.sort_order,
                        is_primary=image.is_primary
                        or (not has_primary and position == 0),
                    )
                )

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to create product") from exc

        logger.info(
            "catalogue.product_created id=%s tenant_id=%s images=%s",
            product.id,
            self.tenant_id,
            len(data.images),
        )

        # Re-read so the selectin-loaded images collection is populated.
        return await self.get(product.id)

    async def get(self, product_id: UUID) -> Product:
        product = await self.products.get(product_id)

        if product is None:
            raise NotFoundError("Product not found")

        return product

    async def get_public(self, product_id: UUID) -> Product:
        """
        Fetch a product only when it is publicly visible.

        Visibility means the product is ACTIVE *and* its category is active --
        the same rule the storefront listing applies -- so a product cannot be
        reached by id after its category is switched off.
        """
        product = await self.get(product_id)

        if product.status != CatalogueStatus.ACTIVE.value:
            raise NotFoundError("Product not found")

        category = await self.categories.get(product.category_id)
        if category is None or not category.is_active:
            raise NotFoundError("Product not found")

        return product

    async def list(
        self,
        params: PageParams,
        *,
        category_id: UUID | None = None,
        active_only: bool = False,
    ) -> tuple[list[Product], int]:
        """
        List products for the tenant.

        active_only=True is intended for public/storefront usage.

        Filtering happens at the database query level before
        pagination, so pagination totals remain correct.
        """
        if category_id is not None:
            await self._require_category(category_id)

        stmt = self.products.list_select(
            category_id=category_id,
            active_only=active_only,
        )

        rows, total = await self.products.paginate(
            stmt,
            params,
        )

        return list(rows), total

    async def update(
        self,
        product_id: UUID,
        data: ProductUpdate,
    ) -> Product:
        product = await self.get(product_id)

        changes = data.model_dump(exclude_unset=True)

        if "category_id" in changes and changes["category_id"] is not None:
            await self._require_category(changes["category_id"])

        if "status" in changes and changes["status"] is not None:
            changes["status"] = changes["status"].value

        for field, value in changes.items():
            setattr(product, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to update product") from exc

        logger.info(
            "catalogue.product_updated id=%s tenant_id=%s",
            product.id,
            self.tenant_id,
        )

        return product

    async def delete(self, product_id: UUID) -> None:
        """
        Archive the product and its variants instead of deleting them.

        Products may later be referenced by orders/order items, so the record
        is kept to preserve historical commerce data. Variants are archived in
        the same transaction -- otherwise they stay individually readable on
        the storefront after their parent product is gone.
        """
        product = await self.get(product_id)

        if product.status == CatalogueStatus.ARCHIVED.value:
            return

        product.status = "ARCHIVED"

        archived_variants = await self.session.execute(
            update(ProductVariant)
            .where(
                ProductVariant.tenant_id == self.tenant_id,
                ProductVariant.product_id == product_id,
                ProductVariant.status != CatalogueStatus.ARCHIVED.value,
            )
            .values(status=CatalogueStatus.ARCHIVED.value)
        )

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "Unable to archive product"
            ) from exc

        logger.info(
            "catalogue.product_archived id=%s tenant_id=%s variants_archived=%s",
            product_id,
            self.tenant_id,
            archived_variants.rowcount or 0,
        )


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

    async def create(
        self,
        product_id: UUID,
        data: VariantCreate,
    ) -> ProductVariant:
        product = await self._require_product(product_id)

        if product.status == CatalogueStatus.ARCHIVED.value:
            raise ConflictError(
                "Cannot add a variant to an archived product"
            )

        sku = _normalise_sku(data.sku)

        if await self.variants.get_by_sku(sku) is not None:
            raise ConflictError(
                "A variant with this SKU already exists"
            )

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
            raise ConflictError(
                "A variant with this SKU already exists"
            ) from exc

        logger.info(
            "catalogue.variant_created id=%s tenant_id=%s",
            variant.id,
            self.tenant_id,
        )

        return variant

    async def get(self, variant_id: UUID) -> ProductVariant:
        variant = await self.variants.get(variant_id)

        if variant is None:
            raise NotFoundError("Variant not found")

        return variant

    async def list_for_product(
        self,
        product_id: UUID,
        params: PageParams,
        *,
        active_only: bool = False,
    ) -> tuple[list[ProductVariant], int]:
        """
        List variants belonging to a product.

        active_only=True is intended for public/storefront usage.
        """
        await self._require_product(product_id)

        stmt = self.variants.list_select(
            product_id,
            active_only=active_only,
        )

        rows, total = await self.variants.paginate(
            stmt,
            params,
        )

        return list(rows), total

    async def update(
        self,
        variant_id: UUID,
        data: VariantUpdate,
    ) -> ProductVariant:
        variant = await self.get(variant_id)

        changes = data.model_dump(exclude_unset=True)

        if "sku" in changes and changes["sku"] is not None:
            sku = _normalise_sku(changes["sku"])

            existing = await self.variants.get_by_sku(sku)

            if existing is not None and existing.id != variant.id:
                raise ConflictError(
                    "A variant with this SKU already exists"
                )

            changes["sku"] = sku

        if "status" in changes and changes["status"] is not None:
            changes["status"] = changes["status"].value

        for field, value in changes.items():
            setattr(variant, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "A variant with this SKU already exists"
            ) from exc

        logger.info(
            "catalogue.variant_updated id=%s tenant_id=%s",
            variant.id,
            self.tenant_id,
        )

        return variant

    async def delete(self, variant_id: UUID) -> None:
        """
        Archive the variant instead of physically deleting it.

        Variants may later be referenced by cart/order/order-item records.
        """
        variant = await self.get(variant_id)

        if variant.status == CatalogueStatus.ARCHIVED.value:
            return

        variant.status = "ARCHIVED"

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "Unable to archive variant"
            ) from exc

        logger.info(
            "catalogue.variant_archived id=%s tenant_id=%s",
            variant_id,
            self.tenant_id,
        )


class ProductImageService:
    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id

        self.images = ProductImageRepository(
            session,
            tenant_id,
        )

        self.products = ProductRepository(
            session,
            tenant_id,
        )

    async def _require_product(
        self,
        product_id: UUID,
    ) -> Product:
        product = await self.products.get(product_id)

        if product is None:
            raise NotFoundError("Product not found")

        return product

    async def list_for_product(
        self,
        product_id: UUID,
    ) -> list[ProductImage]:
        await self._require_product(product_id)

        result = await self.session.scalars(
            self.images.list_select(product_id)
        )

        return list(result.all())

    async def add(
        self,
        product_id: UUID,
        data: ProductImageCreate,
    ) -> ProductImage:
        product = await self._require_product(product_id)

        if product.status == CatalogueStatus.ARCHIVED.value:
            raise ConflictError(
                "Cannot add an image to an archived product"
            )

        if data.is_primary:
            await self._remove_primary(product_id)

        image = ProductImage(
            product_id=product_id,
            url=data.url.strip(),
            alt_text=(
                data.alt_text.strip()
                if data.alt_text
                else None
            ),
            sort_order=data.sort_order,
            is_primary=data.is_primary,
        )

        try:
            self.session.add(image)
            await self.session.commit()
            await self.session.refresh(image)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "Unable to add product image"
            ) from exc

        logger.info(
            "catalogue.product_image_created "
            "id=%s product_id=%s tenant_id=%s",
            image.id,
            product_id,
            self.tenant_id,
        )

        return image

    async def update(
        self,
        image_id: UUID,
        data: ProductImageUpdate,
    ) -> ProductImage:
        image = await self.images.get(image_id)

        if image is None:
            raise NotFoundError("Product image not found")

        changes = data.model_dump(
            exclude_unset=True
        )

        if changes.get("is_primary") is True:
            await self._remove_primary(
                image.product_id,
                exclude_id=image.id,
            )

        for field, value in changes.items():
            if field in {"url", "alt_text"} and value is not None:
                value = value.strip()

            setattr(image, field, value)

        try:
            await self.session.commit()
            await self.session.refresh(image)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "Unable to update product image"
            ) from exc

        logger.info(
            "catalogue.product_image_updated "
            "id=%s tenant_id=%s",
            image.id,
            self.tenant_id,
        )

        return image

    async def delete(
        self,
        image_id: UUID,
    ) -> None:
        image = await self.images.get(image_id)

        if image is None:
            raise NotFoundError("Product image not found")

        await self.images.delete(image)
        await self.session.commit()

        logger.info(
            "catalogue.product_image_deleted "
            "id=%s tenant_id=%s",
            image_id,
            self.tenant_id,
        )

    async def _remove_primary(
        self,
        product_id: UUID,
        exclude_id: UUID | None = None,
    ) -> None:
        images = await self.session.scalars(
            self.images.list_select(product_id)
        )

        for image in images:
            if exclude_id is not None and image.id == exclude_id:
                continue

            if image.is_primary:
                image.is_primary = False
