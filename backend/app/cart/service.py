from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cart.models import Cart
from app.cart.repository import CartItemRepository, CartRepository
from app.cart.schemas import CartItemCreate, CartItemImage, CartItemRead, CartItemUpdate, CartRead
from app.catalogue.constants import CatalogueStatus
from app.catalogue.repository import ProductRepository, VariantRepository
from app.catalogue.serializers import sellable_quantity
from app.catalogue.service import InventoryService
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger

logger = get_logger("cart")

VARIANT_NOT_FOUND = "Product variant not found"
VARIANT_UNAVAILABLE = "Product variant is not available"
PRODUCT_UNAVAILABLE = "Product is not available"
ITEM_NOT_FOUND = "Cart item not found"


class CartService:
    """Cart operations; adding never reserves stock."""

    def __init__(self, session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.customer_id = customer_id

        self.carts = CartRepository(session, tenant_id)
        self.items = CartItemRepository(session, tenant_id)
        self.variants = VariantRepository(session, tenant_id)
        self.products = ProductRepository(session, tenant_id)
        self.inventory = InventoryService(session, tenant_id)

    async def get_or_create_cart(self) -> Cart:
        """The customer's active cart, created on first use."""
        cart = await self.carts.get_active(self.customer_id)
        if cart is not None:
            return cart

        try:
            cart = await self.carts.create(self.customer_id)
            await self.session.commit()
            return cart
        except IntegrityError:
            await self.session.rollback()
            existing = await self.carts.get_active(self.customer_id)
            if existing is None:
                raise
            return existing

    async def view(self) -> CartRead:
        cart = await self.get_or_create_cart()
        return await self._render(cart)

    async def clear(self) -> CartRead:
        """Empty the cart but keep it, so the customer keeps the same cart id."""
        cart = await self.get_or_create_cart()

        removed = await self.items.clear(cart.id)
        await self.session.commit()

        logger.info(
            "cart.cleared cart_id=%s tenant_id=%s items=%s",
            cart.id,
            self.tenant_id,
            removed,
        )
        return await self._render(cart)

    async def add_item(self, data: CartItemCreate) -> CartRead:
        cart = await self.get_or_create_cart()

        existing = await self.items.get_by_variant(cart.id, data.variant_id)
        wanted = data.quantity + (existing.quantity if existing else 0)

        await self._check_available(data.variant_id, wanted)

        try:
            if existing is not None:
                existing.quantity = wanted
            else:
                await self.items.add_item(cart.id, data.variant_id, data.quantity)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            return await self._top_up(cart, data)

        logger.info(
            "cart.item_added cart_id=%s tenant_id=%s variant_id=%s quantity=%s",
            cart.id,
            self.tenant_id,
            data.variant_id,
            wanted,
        )
        return await self._render(cart)

    async def _top_up(self, cart: Cart, data: CartItemCreate) -> CartRead:
        existing = await self.items.get_by_variant(cart.id, data.variant_id)
        if existing is None:
            raise ConflictError("Could not update the cart, please try again")

        wanted = existing.quantity + data.quantity
        await self._check_available(data.variant_id, wanted)

        existing.quantity = wanted
        await self.session.commit()
        return await self._render(cart)

    async def update_item(self, item_id: UUID, data: CartItemUpdate) -> CartRead:
        cart = await self.get_or_create_cart()

        item = await self.items.get_item(cart.id, item_id)
        if item is None:
            raise NotFoundError(ITEM_NOT_FOUND)

        await self._check_available(item.variant_id, data.quantity)

        item.quantity = data.quantity
        await self.session.commit()

        logger.info(
            "cart.item_updated cart_id=%s tenant_id=%s item_id=%s quantity=%s",
            cart.id,
            self.tenant_id,
            item_id,
            data.quantity,
        )
        return await self._render(cart)

    async def remove_item(self, item_id: UUID) -> CartRead:
        cart = await self.get_or_create_cart()

        item = await self.items.get_item(cart.id, item_id)
        if item is None:
            raise NotFoundError(ITEM_NOT_FOUND)

        await self.items.delete(item)
        await self.session.commit()

        logger.info(
            "cart.item_removed cart_id=%s tenant_id=%s item_id=%s",
            cart.id,
            self.tenant_id,
            item_id,
        )
        return await self._render(cart)

    async def _check_available(self, variant_id: UUID, quantity: int) -> None:
        """Check stock for this quantity; nothing is reserved here."""
        variant = await self.variants.get(variant_id)
        if variant is None:
            raise NotFoundError(VARIANT_NOT_FOUND)

        if variant.status != CatalogueStatus.ACTIVE.value:
            raise ConflictError(VARIANT_UNAVAILABLE)

        product = await self.products.get(variant.product_id)
        if product is None or product.status != CatalogueStatus.ACTIVE.value:
            raise ConflictError(PRODUCT_UNAVAILABLE)

        available = sellable_quantity(await self.inventory.get(variant_id))
        if quantity > available:
            if available == 0:
                raise ConflictError(
                    "This item is out of stock", error_code="INSUFFICIENT_STOCK"
                )
            raise ConflictError(
                f"Only {available} items are available",
                error_code="INSUFFICIENT_STOCK",
            )

    async def _render(self, cart: Cart) -> CartRead:
        rows = await self.items.list_with_catalogue(cart.id)
        images = await self.items.primary_images(
            [product.id for _item, _variant, product in rows]
        )

        items: list[CartItemRead] = []
        subtotal = Decimal("0.00")
        count = 0

        for item, variant, product in rows:
            line_total = variant.price * item.quantity
            subtotal += line_total
            count += item.quantity

            items.append(
                CartItemRead(
                    id=item.id,
                    variant_id=variant.id,
                    product_id=product.id,
                    product_name=product.name,
                    variant_name=variant.name,
                    sku=variant.sku,
                    quantity=item.quantity,
                    unit_price=variant.price,
                    subtotal=line_total,
                    image=_image_of(images.get(product.id)),
                )
            )

        return CartRead(
            id=cart.id, items=items, subtotal=subtotal, item_count=count
        )


def _image_of(image) -> CartItemImage | None:
    if image is None:
        return None
    return CartItemImage(url=image.url, alt_text=image.alt_text)
