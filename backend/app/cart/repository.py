from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, delete, select

from app.cart.models import Cart, CartItem, CartStatus
from app.catalogue.models import Product, ProductImage, ProductVariant
from app.core.repository import TenantScopedRepository


class CartRepository(TenantScopedRepository[Cart]):
    model = Cart

    async def get_active(self, customer_id: UUID) -> Cart | None:
        return await self.find_one(
            Cart.customer_id == customer_id,
            Cart.status == CartStatus.ACTIVE.value,
        )

    async def create(self, customer_id: UUID) -> Cart:
        return await self.add(
            Cart(customer_id=customer_id, status=CartStatus.ACTIVE.value)
        )


class CartItemRepository(TenantScopedRepository[CartItem]):
    model = CartItem

    async def get_item(self, cart_id: UUID, item_id: UUID) -> CartItem | None:
        return await self.find_one(CartItem.cart_id == cart_id, CartItem.id == item_id)

    async def get_by_variant(self, cart_id: UUID, variant_id: UUID) -> CartItem | None:
        return await self.find_one(
            CartItem.cart_id == cart_id, CartItem.variant_id == variant_id
        )

    async def add_item(self, cart_id: UUID, variant_id: UUID, quantity: int) -> CartItem:
        return await self.add(
            CartItem(cart_id=cart_id, variant_id=variant_id, quantity=quantity)
        )

    async def clear(self, cart_id: UUID) -> int:
        result = await self.session.execute(
            delete(CartItem).where(
                CartItem.tenant_id == self.tenant_id, CartItem.cart_id == cart_id
            )
        )
        await self.session.flush()
        return result.rowcount or 0

    async def list_with_catalogue(
        self, cart_id: UUID
    ) -> list[tuple[CartItem, ProductVariant, Product]]:
        """
        Every cart line with the variant and product it points at.

        One join rather than a lookup per item, so rendering a cart costs a
        fixed number of queries however many lines it has.
        """
        stmt = (
            select(CartItem, ProductVariant, Product)
            .join(
                ProductVariant,
                and_(
                    ProductVariant.id == CartItem.variant_id,
                    ProductVariant.tenant_id == CartItem.tenant_id,
                ),
            )
            .join(
                Product,
                and_(
                    Product.id == ProductVariant.product_id,
                    Product.tenant_id == ProductVariant.tenant_id,
                ),
            )
            .where(CartItem.tenant_id == self.tenant_id, CartItem.cart_id == cart_id)
            .order_by(CartItem.created_at)
        )
        return list((await self.session.execute(stmt)).all())

    async def primary_images(
        self, product_ids: list[UUID]
    ) -> dict[UUID, ProductImage]:
        """Primary image per product, fetched for the whole cart in one query."""
        if not product_ids:
            return {}

        rows = await self.session.scalars(
            select(ProductImage).where(
                ProductImage.tenant_id == self.tenant_id,
                ProductImage.product_id.in_(product_ids),
                ProductImage.is_primary.is_(True),
            )
        )
        return {image.product_id: image for image in rows.all()}
