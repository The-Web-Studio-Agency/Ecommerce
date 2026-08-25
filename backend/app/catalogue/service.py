from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalogue.constants import (
    MAX_OPTIONS_PER_PRODUCT,
    MIN_PRODUCT_IMAGES,
    CatalogueStatus,
    InventoryReason,
    ProductSort,
)
from app.catalogue.models import (
    Category,
    InventoryItem,
    InventoryMovement,
    Product,
    ProductImage,
    ProductOption,
    ProductVariant,
    ProductVariantOption,
)
from app.catalogue.repository import (
    CategoryRepository,
    InventoryRepository,
    ProductImageRepository,
    ProductOptionRepository,
    ProductRepository,
    VariantOptionRepository,
    VariantRepository,
)
from app.catalogue.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ImageReorderPayload,
    ProductCreate,
    ProductImageCreate,
    ProductImageUpdate,
    ProductUpdate,
    VariantCreate,
    VariantOptionValue,
    VariantUpdate,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.pagination import PageParams

logger = get_logger("catalogue")

PRODUCT_NOT_FOUND = "Product not found"
CATEGORY_NOT_FOUND = "Category not found"
VARIANT_NOT_FOUND = "Variant not found"
IMAGE_NOT_FOUND = "Product image not found"
LAST_IMAGE = "A product must have at least one image"


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
            status=data.status.value,
        )
        try:
            await self.categories.add(category)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to create category") from exc

        logger.info(
            "catalogue.category_created id=%s tenant_id=%s", category.id, self.tenant_id
        )
        return category

    async def get(self, category_id: UUID) -> Category:
        category = await self.categories.get(category_id)
        if category is None:
            raise NotFoundError(CATEGORY_NOT_FOUND)
        return category

    async def get_public(self, category_id: UUID) -> Category:
        category = await self.get(category_id)
        if category.status != CatalogueStatus.ACTIVE.value:
            raise NotFoundError(CATEGORY_NOT_FOUND)
        return category

    async def list(
        self, params: PageParams, *, active_only: bool = False
    ) -> tuple[list[Category], int]:
        stmt = self.categories.list_select(active_only=active_only)
        rows, total = await self.categories.paginate(stmt, params)
        return list(rows), total

    async def update(self, category_id: UUID, data: CategoryUpdate) -> Category:
        category = await self.get(category_id)
        changes = data.model_dump(exclude_unset=True)

        if changes.get("status") is not None:
            changes["status"] = changes["status"].value

        for field, value in changes.items():
            setattr(category, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to update category") from exc

        logger.info(
            "catalogue.category_updated id=%s tenant_id=%s", category.id, self.tenant_id
        )
        return category

    async def delete(self, category_id: UUID) -> None:
        """
        Archive the category rather than removing the row.

        Archived products keep a foreign key to their category, so a hard delete
        would either fail or orphan order history. Archiving keeps the reference
        resolvable and matches how products and variants already behave.

        Only live products block this: a category whose products are all
        archived has nothing left to protect.
        """
        category = await self.get(category_id)

        if category.status == CatalogueStatus.ARCHIVED.value:
            return

        if await self.products.has_products_in_category(category.id):
            raise ConflictError("Category still has active products and cannot be deleted")

        category.status = CatalogueStatus.ARCHIVED.value
        await self.session.commit()

        logger.info(
            "catalogue.category_archived id=%s tenant_id=%s", category_id, self.tenant_id
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
            raise NotFoundError(CATEGORY_NOT_FOUND)
        if category.status == CatalogueStatus.ARCHIVED.value:
            raise ConflictError("Category is archived and cannot take products")
        return category

    async def create(self, data: ProductCreate) -> Product:
        """
        Create a product together with its images in one transaction.

        The schema requires at least one image, and both rows are written
        atomically, so a product never exists in an image-less state.
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
        return await self.get(product.id)

    async def get(self, product_id: UUID) -> Product:
        product = await self.products.get(product_id)
        if product is None:
            raise NotFoundError(PRODUCT_NOT_FOUND)
        return product

    async def get_public(self, product_id: UUID) -> Product:
        """
        Fetch a product only when it is publicly visible.

        Visible means ACTIVE *and* in an active category -- the same rule the
        listing applies, so a product cannot be reached by id after its category
        is retired.
        """
        product = await self.get(product_id)

        if product.status != CatalogueStatus.ACTIVE.value:
            raise NotFoundError(PRODUCT_NOT_FOUND)

        category = await self.categories.get(product.category_id)
        if category is None or category.status != CatalogueStatus.ACTIVE.value:
            raise NotFoundError(PRODUCT_NOT_FOUND)

        return product

    async def list(
        self,
        params: PageParams,
        *,
        category_id: UUID | None = None,
        search: str | None = None,
        brand: str | None = None,
        featured: bool | None = None,
        min_price=None,
        max_price=None,
        sort: ProductSort = ProductSort.NAME_ASC,
        active_only: bool = False,
    ) -> tuple[list[Product], int]:
        if category_id is not None:
            category = await self.categories.get(category_id)
            if category is None:
                raise NotFoundError(CATEGORY_NOT_FOUND)

        stmt = self.products.list_select(
            category_id=category_id,
            search=search,
            brand=brand,
            featured=featured,
            min_price=min_price,
            max_price=max_price,
            sort=sort,
            active_only=active_only,
        )
        rows, total = await self.products.paginate(stmt, params)
        return list(rows), total

    async def update(self, product_id: UUID, data: ProductUpdate) -> Product:
        product = await self.get(product_id)
        changes = data.model_dump(exclude_unset=True)

        if changes.get("category_id") is not None:
            await self._require_category(changes["category_id"])

        if changes.get("status") is not None:
            changes["status"] = changes["status"].value

        for field, value in changes.items():
            setattr(product, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to update product") from exc

        logger.info(
            "catalogue.product_updated id=%s tenant_id=%s", product.id, self.tenant_id
        )
        return await self.get(product.id)

    async def delete(self, product_id: UUID) -> None:
        """
        Archive the product and its variants.

        Orders will reference both, so the rows stay. Variants are archived in
        the same transaction, otherwise they remain individually readable on the
        storefront after their parent product is gone.
        """
        product = await self.get(product_id)

        if product.status == CatalogueStatus.ARCHIVED.value:
            return

        product.status = CatalogueStatus.ARCHIVED.value

        archived = await self.session.execute(
            update(ProductVariant)
            .where(
                ProductVariant.tenant_id == self.tenant_id,
                ProductVariant.product_id == product_id,
                ProductVariant.status != CatalogueStatus.ARCHIVED.value,
            )
            .values(status=CatalogueStatus.ARCHIVED.value)
        )

        await self.session.commit()

        logger.info(
            "catalogue.product_archived id=%s tenant_id=%s variants_archived=%s",
            product_id,
            self.tenant_id,
            archived.rowcount or 0,
        )


class VariantService:
    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.variants = VariantRepository(session, tenant_id)
        self.products = ProductRepository(session, tenant_id)
        self.options = ProductOptionRepository(session, tenant_id)
        self.variant_options = VariantOptionRepository(session, tenant_id)
        self.inventory = InventoryRepository(session, tenant_id)

    async def _require_product(self, product_id: UUID) -> Product:
        product = await self.products.get(product_id)
        if product is None:
            raise NotFoundError(PRODUCT_NOT_FOUND)
        return product

    async def _sync_options(
        self, product_id: UUID, variant_id: UUID, options: list[VariantOptionValue]
    ) -> None:
        """
        Attach structured option values to a variant.

        Option names live on the product so every variant shares one "Color"
        rather than inventing its own; the value is what varies per variant.
        """
        existing = list(
            (await self.session.scalars(self.options.list_select(product_id))).all()
        )
        by_name = {option.name.lower(): option for option in existing}

        for entry in options:
            option = by_name.get(entry.name.lower())
            if option is None:
                if len(by_name) >= MAX_OPTIONS_PER_PRODUCT:
                    raise ConflictError(
                        f"A product may have at most {MAX_OPTIONS_PER_PRODUCT} options"
                    )
                option = await self.options.add(
                    ProductOption(
                        product_id=product_id,
                        name=entry.name,
                        position=len(by_name),
                    )
                )
                by_name[entry.name.lower()] = option

            await self.variant_options.add(
                ProductVariantOption(
                    variant_id=variant_id,
                    option_id=option.id,
                    value=entry.value,
                )
            )

    async def create(self, product_id: UUID, data: VariantCreate) -> ProductVariant:
        product = await self._require_product(product_id)

        if product.status == CatalogueStatus.ARCHIVED.value:
            raise ConflictError("Cannot add a variant to an archived product")

        sku = data.sku.strip().upper()
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
            await self._sync_options(product_id, variant.id, data.options)

            # Every variant gets an inventory row at birth, so stock operations
            # never have to cope with a missing record.
            await self.inventory.add(
                InventoryItem(
                    variant_id=variant.id,
                    available_quantity=data.initial_quantity,
                    reserved_quantity=0,
                    low_stock_threshold=data.low_stock_threshold,
                )
            )
            if data.initial_quantity:
                self.session.add(
                    InventoryMovement(
                        tenant_id=self.tenant_id,
                        variant_id=variant.id,
                        delta=data.initial_quantity,
                        reason=InventoryReason.INITIAL.value,
                    )
                )

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A variant with this SKU already exists") from exc

        logger.info(
            "catalogue.variant_created id=%s tenant_id=%s", variant.id, self.tenant_id
        )
        return await self.get(variant.id)

    async def get(self, variant_id: UUID) -> ProductVariant:
        variant = await self.variants.get(variant_id)
        if variant is None:
            raise NotFoundError(VARIANT_NOT_FOUND)
        return variant

    async def list_for_product(
        self, product_id: UUID, params: PageParams, *, active_only: bool = False
    ) -> tuple[list[ProductVariant], int]:
        await self._require_product(product_id)
        stmt = self.variants.list_select(product_id, active_only=active_only)
        rows, total = await self.variants.paginate(stmt, params)
        return list(rows), total

    async def update(self, variant_id: UUID, data: VariantUpdate) -> ProductVariant:
        variant = await self.get(variant_id)
        changes = data.model_dump(exclude_unset=True)
        options = changes.pop("options", None)

        if changes.get("sku") is not None:
            sku = changes["sku"].strip().upper()
            existing = await self.variants.get_by_sku(sku)
            if existing is not None and existing.id != variant.id:
                raise ConflictError("A variant with this SKU already exists")
            changes["sku"] = sku

        if changes.get("status") is not None:
            changes["status"] = changes["status"].value

        for field, value in changes.items():
            setattr(variant, field, value)

        try:
            if options is not None:
                await self.variant_options.clear_for_variant(variant.id)
                await self._sync_options(
                    variant.product_id,
                    variant.id,
                    [VariantOptionValue(**entry) for entry in options],
                )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A variant with this SKU already exists") from exc

        logger.info(
            "catalogue.variant_updated id=%s tenant_id=%s", variant.id, self.tenant_id
        )
        return await self.get(variant.id)

    async def delete(self, variant_id: UUID) -> None:
        """Archive the variant; carts and orders will reference it."""
        variant = await self.get(variant_id)

        if variant.status == CatalogueStatus.ARCHIVED.value:
            return

        variant.status = CatalogueStatus.ARCHIVED.value
        await self.session.commit()

        logger.info(
            "catalogue.variant_archived id=%s tenant_id=%s", variant_id, self.tenant_id
        )


class ProductImageService:
    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.images = ProductImageRepository(session, tenant_id)
        self.products = ProductRepository(session, tenant_id)

    async def _require_product(self, product_id: UUID) -> Product:
        product = await self.products.get(product_id)
        if product is None:
            raise NotFoundError(PRODUCT_NOT_FOUND)
        return product

    async def _require_image(self, image_id: UUID) -> ProductImage:
        # Repository is tenant-scoped, so another tenant's image id simply
        # does not resolve -- it reads as "not found" rather than "forbidden".
        image = await self.images.get(image_id)
        if image is None:
            raise NotFoundError(IMAGE_NOT_FOUND)
        return image

    async def list_for_product(self, product_id: UUID) -> list[ProductImage]:
        await self._require_product(product_id)
        result = await self.session.scalars(self.images.list_select(product_id))
        return list(result.all())

    async def add(self, product_id: UUID, data: ProductImageCreate) -> ProductImage:
        product = await self._require_product(product_id)

        if product.status == CatalogueStatus.ARCHIVED.value:
            raise ConflictError("Cannot add an image to an archived product")

        try:
            if data.is_primary:
                await self.images.clear_primary(product_id)

            image = await self.images.add(
                ProductImage(
                    product_id=product_id,
                    url=data.url,
                    alt_text=data.alt_text,
                    sort_order=data.sort_order,
                    is_primary=data.is_primary,
                )
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to add product image") from exc

        logger.info(
            "catalogue.product_image_created id=%s product_id=%s tenant_id=%s",
            image.id,
            product_id,
            self.tenant_id,
        )
        return image

    async def update(self, image_id: UUID, data: ProductImageUpdate) -> ProductImage:
        image = await self._require_image(image_id)
        changes = data.model_dump(exclude_unset=True)

        try:
            if changes.get("is_primary") is True:
                await self.images.clear_primary(image.product_id, exclude_id=image.id)

            for field, value in changes.items():
                setattr(image, field, value)

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            # The partial unique index fired: another request claimed primary
            # between our clear and our write.
            raise ConflictError(
                "Another image was set as primary, please retry"
            ) from exc

        logger.info(
            "catalogue.product_image_updated id=%s tenant_id=%s", image.id, self.tenant_id
        )
        return image

    async def set_primary(self, image_id: UUID) -> ProductImage:
        image = await self._require_image(image_id)

        try:
            await self.images.clear_primary(image.product_id, exclude_id=image.id)
            image.is_primary = True
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Another image was set as primary, please retry") from exc

        logger.info(
            "catalogue.product_image_primary id=%s tenant_id=%s", image.id, self.tenant_id
        )
        return image

    async def reorder(
        self, product_id: UUID, data: ImageReorderPayload
    ) -> list[ProductImage]:
        await self._require_product(product_id)

        current = {image.id: image for image in await self.list_for_product(product_id)}
        unknown = [entry.id for entry in data.images if entry.id not in current]
        if unknown:
            raise NotFoundError(IMAGE_NOT_FOUND)

        for entry in data.images:
            current[entry.id].sort_order = entry.sort_order

        await self.session.commit()

        logger.info(
            "catalogue.product_images_reordered product_id=%s tenant_id=%s count=%s",
            product_id,
            self.tenant_id,
            len(data.images),
        )
        return await self.list_for_product(product_id)

    async def delete(self, image_id: UUID) -> None:
        """
        Remove an image, refusing to take a product's last one.

        The product row is locked first so that two concurrent deletes are
        serialised: the second waits, re-counts after the first commits, and
        sees one image left rather than the two both would have seen.
        """
        image = await self._require_image(image_id)

        await self.products.lock(image.product_id)

        remaining = await self.images.count_for_product(image.product_id)
        if remaining <= MIN_PRODUCT_IMAGES:
            raise ConflictError(LAST_IMAGE)

        was_primary = image.is_primary
        product_id = image.product_id
        await self.images.delete(image)

        if was_primary:
            # Keep the invariant that a product with images has a primary one.
            successor = await self.session.scalar(
                self.images.list_select(product_id).limit(1)
            )
            if successor is not None:
                successor.is_primary = True

        await self.session.commit()

        logger.info(
            "catalogue.product_image_deleted id=%s tenant_id=%s", image_id, self.tenant_id
        )


class InventoryService:
    """
    Stock operations.

    Every mutation goes through a conditional UPDATE in the repository, so the
    precondition is checked by PostgreSQL under the row lock rather than in a
    read-then-write window a concurrent order could slip into. A refused update
    surfaces as a ConflictError.

    `reserve`, `release` and `fulfil` take `commit=False` so checkout can call
    them inside its own transaction: the stock change is flushed but not
    committed, and rolls back with the rest if a later step fails.
    """

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.inventory = InventoryRepository(session, tenant_id)
        self.variants = VariantRepository(session, tenant_id)

    async def _require_item(self, variant_id: UUID) -> InventoryItem:
        if await self.variants.get(variant_id) is None:
            raise NotFoundError(VARIANT_NOT_FOUND)

        item = await self.inventory.get_for_variant(variant_id)
        if item is None:
            raise NotFoundError("Inventory record not found")
        return item

    def _record(
        self,
        variant_id: UUID,
        delta: int,
        reason: InventoryReason,
        reference: str | None = None,
        note: str | None = None,
    ) -> None:
        self.session.add(
            InventoryMovement(
                tenant_id=self.tenant_id,
                variant_id=variant_id,
                delta=delta,
                reason=reason.value,
                reference=reference,
                note=note,
            )
        )

    async def _save(self, commit: bool) -> None:
        """Commit on our own, or leave the change to the caller's transaction."""
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()

    async def get(self, variant_id: UUID) -> InventoryItem:
        return await self._require_item(variant_id)

    async def set_available(
        self, variant_id: UUID, quantity: int, note: str | None = None
    ) -> InventoryItem:
        item = await self._require_item(variant_id)
        delta = quantity - item.available_quantity

        if not await self.inventory.set_available(variant_id, quantity):
            raise ConflictError(
                "Stock cannot be set below the quantity already reserved"
            )

        self._record(variant_id, delta, InventoryReason.ADJUSTMENT, note=note)
        await self.session.commit()

        logger.info(
            "inventory.set variant_id=%s tenant_id=%s quantity=%s",
            variant_id,
            self.tenant_id,
            quantity,
        )
        return await self._require_item(variant_id)

    async def adjust(
        self,
        variant_id: UUID,
        delta: int,
        reason: InventoryReason = InventoryReason.ADJUSTMENT,
        reference: str | None = None,
        note: str | None = None,
    ) -> InventoryItem:
        await self._require_item(variant_id)

        if not await self.inventory.adjust_available(variant_id, delta):
            raise ConflictError(
                "Stock cannot go negative or below the quantity already reserved"
            )

        self._record(variant_id, delta, reason, reference, note)
        await self.session.commit()

        logger.info(
            "inventory.adjusted variant_id=%s tenant_id=%s delta=%s",
            variant_id,
            self.tenant_id,
            delta,
        )
        return await self._require_item(variant_id)

    async def set_threshold(self, variant_id: UUID, threshold: int) -> InventoryItem:
        await self._require_item(variant_id)
        await self.inventory.set_threshold(variant_id, threshold)
        await self.session.commit()
        return await self._require_item(variant_id)

    async def reserve(
        self,
        variant_id: UUID,
        quantity: int,
        reference: str | None = None,
        *,
        commit: bool = True,
    ) -> InventoryItem:
        """Hold stock for an order that has not shipped yet."""
        await self._require_item(variant_id)

        if not await self.inventory.reserve(variant_id, quantity):
            raise ConflictError(
                "Insufficient stock", error_code="INSUFFICIENT_STOCK"
            )

        self._record(variant_id, 0, InventoryReason.RESERVATION, reference)
        await self._save(commit)
        return await self._require_item(variant_id)

    async def release(
        self,
        variant_id: UUID,
        quantity: int,
        reference: str | None = None,
        *,
        commit: bool = True,
    ) -> InventoryItem:
        """Give reserved stock back, e.g. when an order is cancelled."""
        await self._require_item(variant_id)

        if not await self.inventory.release(variant_id, quantity):
            raise ConflictError("Cannot release more stock than is reserved")

        self._record(variant_id, 0, InventoryReason.RELEASE, reference)
        await self._save(commit)
        return await self._require_item(variant_id)

    async def fulfil(
        self,
        variant_id: UUID,
        quantity: int,
        reference: str | None = None,
        *,
        commit: bool = True,
    ) -> InventoryItem:
        """Ship reserved stock: it leaves the shelf and the reservation ends."""
        await self._require_item(variant_id)

        if not await self.inventory.fulfil(variant_id, quantity):
            raise ConflictError("Cannot fulfil more stock than is reserved")

        self._record(variant_id, -quantity, InventoryReason.FULFILLMENT, reference)
        await self._save(commit)
        return await self._require_item(variant_id)

    async def movements(
        self, variant_id: UUID, params: PageParams
    ) -> tuple[list[InventoryMovement], int]:
        await self._require_item(variant_id)

        stmt = (
            select(InventoryMovement)
            .where(
                InventoryMovement.tenant_id == self.tenant_id,
                InventoryMovement.variant_id == variant_id,
            )
            .order_by(InventoryMovement.created_at.desc())
        )
        total = await self.session.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        rows = await self.session.scalars(
            stmt.offset(params.offset).limit(params.limit)
        )
        return list(rows.all()), int(total or 0)
