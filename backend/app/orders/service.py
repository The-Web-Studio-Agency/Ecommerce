from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.addresses.models import Address
from app.addresses.repository import AddressRepository
from app.cart.models import Cart, CartStatus
from app.cart.repository import CartItemRepository, CartRepository
from app.catalogue.constants import CatalogueStatus
from app.catalogue.serializers import sellable_quantity
from app.catalogue.service import InventoryService
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.pagination import PageParams
from app.orders.constants import (
    ALLOWED_TRANSITIONS,
    ORDER_NUMBER_PREFIX,
    SHIPPING_AMOUNT,
    OrderStatus,
    PaymentStatus,
)
from app.orders.models import ORDER_NUMBER_SEQUENCE, Order, OrderItem
from app.orders.repository import OrderRepository
from app.orders.schemas import CheckoutItem, CheckoutPreview

logger = get_logger("orders")

ORDER_NOT_FOUND = "Order not found"
ADDRESS_NOT_FOUND = "Address not found"
CART_EMPTY = "Your cart is empty"


class CheckoutService:
    """
    Turning a cart into an order.

    The whole flow lives in two methods:

    * `preview` validates the cart and prices it, changing nothing.
    * `place_order` does the same validation, then reserves stock, writes the
      order and marks the cart converted -- all in one transaction.

    Prices are always read from the catalogue. The only thing the client sends
    is which address to deliver to.
    """

    def __init__(self, session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.customer_id = customer_id

        self.carts = CartRepository(session, tenant_id)
        self.cart_items = CartItemRepository(session, tenant_id)
        self.addresses = AddressRepository(session, tenant_id)
        self.orders = OrderRepository(session, tenant_id)
        self.inventory = InventoryService(session, tenant_id)

    async def preview(self) -> CheckoutPreview:
        """Price the cart without touching stock or creating anything."""
        cart = await self._require_active_cart()
        items = await self._priced_items(cart)
        return self._summary(items)

    async def place_order(self, address_id: UUID) -> Order:
        """
        Create the order.

        One transaction from start to finish: if reserving stock for the third
        line fails, the first two reservations and the half-written order roll
        back with it, so a failed checkout leaves nothing behind.
        """
        cart = await self._require_active_cart()
        address = await self._require_address(address_id)
        items = await self._priced_items(cart)
        summary = self._summary(items)

        try:
            order_number = await self._next_order_number()

            # Hold the stock first. The inventory service does this with a
            # conditional UPDATE, so two customers racing for the last unit
            # cannot both succeed -- the loser gets "Insufficient stock".
            for item in items:
                await self.inventory.reserve(
                    item.variant_id, item.quantity, reference=order_number, commit=False
                )

            order = Order(
                tenant_id=self.tenant_id,
                customer_id=self.customer_id,
                order_number=order_number,
                status=OrderStatus.PENDING.value,
                # Payment integration comes later; every order starts unpaid.
                payment_status=PaymentStatus.PENDING.value,
                subtotal=summary.subtotal,
                shipping_amount=summary.shipping_amount,
                total_amount=summary.total_amount,
                delivery_name=address.full_name,
                delivery_phone=address.phone,
                delivery_address_line_1=address.address_line_1,
                delivery_address_line_2=address.address_line_2,
                delivery_city=address.city,
                delivery_state=address.state,
                delivery_postal_code=address.postal_code,
                delivery_country=address.country,
            )
            self.session.add(order)
            await self.session.flush()

            for item in items:
                self.session.add(
                    OrderItem(
                        tenant_id=self.tenant_id,
                        order_id=order.id,
                        variant_id=item.variant_id,
                        product_id=item.product_id,
                        product_name=item.product_name,
                        variant_name=item.variant_name,
                        sku=item.sku,
                        unit_price=item.unit_price,
                        quantity=item.quantity,
                        subtotal=item.subtotal,
                    )
                )

            # The cart is kept, not deleted -- its items stay readable for
            # support and debugging. A converted cart can never be checked out
            # again because `_require_active_cart` only ever looks for an
            # ACTIVE one, and the next add-to-cart creates a fresh cart.
            cart.status = CartStatus.CONVERTED.value

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to place the order, please try again") from exc
        except Exception:
            await self.session.rollback()
            raise

        logger.info(
            "orders.placed order_number=%s tenant_id=%s customer_id=%s items=%s total=%s",
            order_number,
            self.tenant_id,
            self.customer_id,
            len(items),
            summary.total_amount,
        )
        return await OrderService(self.session, self.tenant_id).get(order.id)

    # ---------------------------------------------------------- validation

    async def _require_active_cart(self) -> Cart:
        cart = await self.carts.get_active(self.customer_id)
        if cart is None:
            raise ConflictError(CART_EMPTY)
        return cart

    async def _require_address(self, address_id: UUID) -> Address:
        address = await self.addresses.get_for_customer(self.customer_id, address_id)
        if address is None:
            raise NotFoundError(ADDRESS_NOT_FOUND)
        return address

    async def _priced_items(self, cart: Cart) -> list[CheckoutItem]:
        """
        Check every line and price it from the catalogue.

        The cart stores only a variant id and a quantity, so this is where the
        product name, SKU and price are read -- once, at checkout -- and then
        frozen onto the order.
        """
        rows = await self.cart_items.list_with_catalogue(cart.id)
        if not rows:
            raise ConflictError(CART_EMPTY)

        items: list[CheckoutItem] = []

        for cart_item, variant, product in rows:
            if (
                product.status != CatalogueStatus.ACTIVE.value
                or variant.status != CatalogueStatus.ACTIVE.value
            ):
                raise ConflictError(f"{product.name} is no longer available")

            available = sellable_quantity(await self.inventory.get(variant.id))
            if cart_item.quantity > available:
                raise ConflictError(
                    f"Only {available} left of {product.name}"
                    if available
                    else f"{product.name} is out of stock",
                    error_code="INSUFFICIENT_STOCK",
                )

            items.append(
                CheckoutItem(
                    product_id=product.id,
                    variant_id=variant.id,
                    product_name=product.name,
                    variant_name=variant.name,
                    sku=variant.sku,
                    quantity=cart_item.quantity,
                    unit_price=variant.price,
                    subtotal=variant.price * cart_item.quantity,
                )
            )

        return items

    def _summary(self, items: list[CheckoutItem]) -> CheckoutPreview:
        subtotal = sum((item.subtotal for item in items), Decimal("0.00"))
        shipping = Decimal(SHIPPING_AMOUNT)

        return CheckoutPreview(
            items=items,
            subtotal=subtotal,
            shipping_amount=shipping,
            total_amount=subtotal + shipping,
        )

    async def _next_order_number(self) -> str:
        """ORD-100001, ORD-100002, ... straight from a Postgres sequence."""
        number = await self.session.scalar(select(ORDER_NUMBER_SEQUENCE.next_value()))
        return f"{ORDER_NUMBER_PREFIX}{number}"


class OrderService:
    """
    Reading orders back, and moving them through fulfilment.

    Constructed with a tenant id, so every query it runs is already scoped to
    one storefront. Customer-facing methods take a customer id as well.
    """

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.orders = OrderRepository(session, tenant_id)
        self.inventory = InventoryService(session, tenant_id)

    async def get(self, order_id: UUID) -> Order:
        """Admin lookup: any order in this tenant."""
        order = await self.orders.get(order_id)
        if order is None:
            raise NotFoundError(ORDER_NOT_FOUND)
        return order

    async def get_for_customer(self, customer_id: UUID, order_id: UUID) -> Order:
        """
        Customer lookup: their own orders only.

        Another customer's order and another tenant's order both fall out as
        "not found", so neither can be probed for existence.
        """
        order = await self.orders.get_for_customer(customer_id, order_id)
        if order is None:
            raise NotFoundError(ORDER_NOT_FOUND)
        return order

    async def list(
        self,
        params: PageParams,
        *,
        customer_id: UUID | None = None,
        order_number: str | None = None,
        status: OrderStatus | None = None,
        payment_status: PaymentStatus | None = None,
    ) -> tuple[list[Order], int]:
        stmt = self.orders.list_select(
            customer_id=customer_id,
            order_number=order_number,
            status=status,
            payment_status=payment_status,
        )
        rows, total = await self.orders.paginate(stmt, params)
        return list(rows), total

    async def update_status(self, order_id: UUID, new_status: OrderStatus) -> Order:
        """
        Move an order to its next status, adjusting stock to match.

        Three of the transitions mean something for inventory:

        * placing an order reserved the stock (see CheckoutService)
        * shipping it means the stock physically leaves -- `fulfil`
        * cancelling it hands the stock back -- `release`

        Everything else only changes the status column.
        """
        order = await self.get(order_id)
        current = OrderStatus(order.status)

        if new_status == current:
            return order

        if new_status not in ALLOWED_TRANSITIONS[current]:
            raise ConflictError(
                f"An order that is {current.value} cannot become {new_status.value}"
            )

        try:
            if new_status is OrderStatus.SHIPPED:
                await self._fulfil_stock(order)
            elif new_status is OrderStatus.CANCELLED:
                await self._release_stock(order)

            order.status = new_status.value
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        logger.info(
            "orders.status_changed order_number=%s tenant_id=%s from=%s to=%s",
            order.order_number,
            self.tenant_id,
            current.value,
            new_status.value,
        )
        return await self.get(order.id)

    async def cancel(self, order_id: UUID) -> Order:
        """Cancel an order and give its reserved stock back."""
        return await self.update_status(order_id, OrderStatus.CANCELLED)

    async def _release_stock(self, order: Order) -> None:
        for item in order.items:
            await self.inventory.release(
                item.variant_id, item.quantity, reference=order.order_number, commit=False
            )

    async def _fulfil_stock(self, order: Order) -> None:
        for item in order.items:
            await self.inventory.fulfil(
                item.variant_id, item.quantity, reference=order.order_number, commit=False
            )
