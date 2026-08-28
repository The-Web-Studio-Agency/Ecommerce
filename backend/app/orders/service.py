from __future__ import annotations

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
from app.core.money import ZERO, money
from app.core.pagination import PageParams
from app.orders.constants import (
    ALLOWED_TRANSITIONS,
    ORDER_NUMBER_PREFIX,
    OrderStatus,
    PaymentStatus,
)
from app.orders.models import ORDER_NUMBER_SEQUENCE, Order, OrderItem
from app.orders.repository import OrderRepository
from app.orders.schemas import CheckoutItem, CheckoutPreview
from app.payments.constants import PaymentProvider
from app.payments.constants import PaymentStatus as CashStatus
from app.payments.models import Payment
from app.payments.repository import PaymentRepository
from app.pricing.service import ShippingService, TaxService

logger = get_logger("orders")

ORDER_NOT_FOUND = "Order not found"
ADDRESS_NOT_FOUND = "Address not found"
CART_EMPTY = "Your cart is empty"

# How far a customer may cancel on their own. Past this the order is being
# picked and packed, so cancelling becomes a conversation with the shop.
CUSTOMER_CANCELLABLE_STATUSES = frozenset({OrderStatus.PENDING, OrderStatus.CONFIRMED})


class CheckoutService:
    """
    Turning a cart into an order.

    The whole flow lives in two methods:

    * `preview` validates the cart and prices it, changing nothing.
    * `place_order` does the same validation, then reserves stock, writes the
      order and its payment, and marks the cart converted -- all in one
      transaction.

    Cash on delivery is the only way to pay, so there is nothing to choose:
    every order gets its payment here, and no order can exist without one.

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
        self.payments = PaymentRepository(session, tenant_id)
        self.shipping = ShippingService(session, tenant_id)
        self.tax = TaxService(session, tenant_id)

    async def preview(self) -> CheckoutPreview:
        """Price the cart without touching stock or creating anything."""
        cart = await self._require_active_cart()
        items = await self._priced_items(cart)
        return await self._summary(items)

    async def place_order(self, address_id: UUID) -> Order:
        """
        Create the order.

        One transaction from start to finish: if reserving stock for the third
        line fails, the first two reservations and the half-written order roll
        back with it, so a failed checkout leaves nothing behind.

        The order starts PENDING and its payment starts PENDING too -- the shop
        confirms the order, and the cash arrives when the courier does.
        """
        cart = await self._require_active_cart()
        address = await self._require_address(address_id)
        items = await self._priced_items(cart)
        summary = await self._summary(items)

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
                # Everything is cash on delivery, so an order is unpaid until
                # the courier hands it over. See OrderService._collect_cash.
                payment_status=PaymentStatus.PENDING.value,
                subtotal=summary.subtotal,
                shipping_amount=summary.shipping_amount,
                tax_amount=summary.tax_amount,
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

            # Cash on delivery, so nothing is collected yet. The row exists
            # from the start so that "what is owed on this order" is never a
            # question the database cannot answer.
            self.session.add(
                Payment(
                    tenant_id=self.tenant_id,
                    order_id=order.id,
                    amount=summary.total_amount,
                    status=CashStatus.PENDING.value,
                    provider=PaymentProvider.COD.value,
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

    async def _summary(self, items: list[CheckoutItem]) -> CheckoutPreview:
        """
        What the basket costs, in the order the amounts depend on each other.

        The goods first, then delivery -- which may be free once the goods are
        expensive enough -- then tax on both, then the total. Every figure is
        read from the tenant's own settings; nothing here comes from the
        request.
        """
        subtotal = money(sum((item.subtotal for item in items), ZERO))
        shipping = await self.shipping.calculate(subtotal)
        tax = await self.tax.calculate(subtotal, shipping)

        return CheckoutPreview(
            items=items,
            subtotal=subtotal,
            shipping_amount=shipping,
            tax_amount=tax,
            total_amount=subtotal + shipping + tax,
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
        self.payments = PaymentRepository(session, tenant_id)

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
        Move an order to its next status, adjusting stock and cash to match.

        Three of the transitions mean something for inventory:

        * placing an order reserved the stock (see CheckoutService)
        * shipping it means the stock physically leaves -- `fulfil`
        * cancelling it hands the stock back -- `release`

        Two of them mean something for the money, because everything is paid
        for in cash on delivery:

        * delivering it is when the cash is actually handed over -- the
          payment becomes PAID
        * cancelling it means the cash never will be -- the payment ends FAILED

        Everything else only changes the status column. All of it commits
        together, so stock, cash and status can never disagree.
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
            elif new_status is OrderStatus.DELIVERED:
                await self._collect_cash(order)
            elif new_status is OrderStatus.CANCELLED:
                await self._release_stock(order)
                await self._abandon_payment(order)

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

    async def cancel_for_customer(self, customer_id: UUID, order_id: UUID) -> Order:
        """
        Let a customer call off their own order.

        Only while the shop has not started packing it. Once an order is
        PROCESSING somebody is already picking stock off a shelf, so from
        there it is the shop's decision -- an admin can still cancel it.

        The cancellation itself goes through `update_status`, so the stock
        comes back and the unpaid COD payment is written off exactly as it
        would be for an admin.
        """
        order = await self.get_for_customer(customer_id, order_id)
        current = OrderStatus(order.status)

        if current is OrderStatus.CANCELLED:
            return order

        if current not in CUSTOMER_CANCELLABLE_STATUSES:
            raise ConflictError(
                f"An order that is {current.value} can no longer be cancelled online. "
                "Please contact the store."
            )

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

    async def _collect_cash(self, order: Order) -> None:
        """
        The courier handed the goods over and took the money.

        Nothing is committed here -- `update_status` owns the transaction, so
        the order is never recorded as delivered without the cash, or paid
        without being delivered.
        """
        payment = await self.payments.get_by_status(order.id, CashStatus.PENDING)
        if payment is None:
            return

        payment.status = CashStatus.PAID.value
        order.payment_status = PaymentStatus.PAID.value

    async def _abandon_payment(self, order: Order) -> None:
        """A cancelled order is never delivered, so its cash never arrives."""
        payment = await self.payments.get_by_status(order.id, CashStatus.PENDING)
        if payment is None:
            return

        payment.status = CashStatus.FAILED.value
