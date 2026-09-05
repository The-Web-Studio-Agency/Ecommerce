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
from app.core.money import ZERO, money
from app.core.pagination import PageParams
from app.coupons.models import Coupon
from app.coupons.service import CouponService
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

CUSTOMER_CANCELLABLE_STATUSES = frozenset({OrderStatus.PENDING, OrderStatus.CONFIRMED})


class CheckoutService:
    """Turning a cart into an order: `preview` prices it, `place_order` writes it."""

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
        self.coupons = CouponService(session, tenant_id)


    async def preview(
        self,
        address_id: UUID | None = None,
        coupon_code: str | None = None,
    ) -> CheckoutPreview:
        """Price the cart without touching stock or creating anything."""
        if address_id is not None:
            await self._require_address(address_id)

        cart = await self._require_active_cart()
        items = await self._priced_items(cart)
        subtotal = self._subtotal(items)

        coupon, discount = await self._resolve_coupon(coupon_code, subtotal, for_update=False)
        return await self._summary(items, subtotal, coupon, discount)

    async def place_order(
        self,
        address_id: UUID,
        coupon_code: str | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> Order:
        """Create the order, its payment and its stock reservations in one transaction."""
        if idempotency_key:
            replayed = await self._replayed_order(idempotency_key)
            if replayed is not None:
                return replayed

        cart = await self._require_active_cart()
        address = await self._require_address(address_id)
        items = await self._priced_items(cart)
        subtotal = self._subtotal(items)

        try:
            order_number = await self._next_order_number()

            for item in items:
                await self.inventory.reserve(
                    item.variant_id, item.quantity, reference=order_number, commit=False
                )

            # Re-validated here, under lock, against the server-computed
            # subtotal -- never the subtotal/discount an earlier preview
            # call may have shown the customer. This is also the only place
            # a coupon actually gets spent (times_used incremented,
            # CouponUsage recorded); a plain preview never reaches this.
            coupon, discount = await self._resolve_coupon(coupon_code, subtotal, for_update=True)
            summary = await self._summary(items, subtotal, coupon, discount)

            order = Order(
                tenant_id=self.tenant_id,
                customer_id=self.customer_id,
                order_number=order_number,
                status=OrderStatus.PENDING.value,
                payment_status=PaymentStatus.PENDING.value,
                subtotal=summary.subtotal,
                coupon_id=coupon.id if coupon else None,
                coupon_code=coupon.code if coupon else None,
                discount_amount=summary.discount_amount,
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
                idempotency_key=idempotency_key,
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

            if coupon is not None:
                # No commit of its own -- shares this transaction, so a
                # failure anywhere below (or above) rolls the redemption
                # back along with the order itself.
                await self.coupons.record_redemption(
                    coupon, self.customer_id, order.id, discount
                )

            self.session.add(
                Payment(
                    tenant_id=self.tenant_id,
                    order_id=order.id,
                    amount=summary.total_amount,
                    status=CashStatus.PENDING.value,
                    provider=PaymentProvider.COD.value,
                )
            )

            cart.status = CartStatus.CONVERTED.value

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()

            if idempotency_key:
                replayed = await self._replayed_order(idempotency_key)
                if replayed is not None:
                    return replayed

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

    async def _replayed_order(self, idempotency_key: str) -> Order | None:
        """The order this customer already placed under the same key, if any."""
        existing = await self.orders.get_by_idempotency_key(
            self.customer_id, idempotency_key
        )
        if existing is None:
            return None

        logger.info(
            "orders.idempotent_replay order_number=%s tenant_id=%s customer_id=%s",
            existing.order_number,
            self.tenant_id,
            self.customer_id,
        )
        return await OrderService(self.session, self.tenant_id).get(existing.id)

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
        """Validate every cart line and price it from the catalogue."""
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

    @staticmethod
    def _subtotal(items: list[CheckoutItem]) -> Decimal:
        return money(sum((item.subtotal for item in items), ZERO))

    async def _resolve_coupon(
        self, coupon_code: str | None, subtotal: Decimal, *, for_update: bool
    ) -> tuple[Coupon | None, Decimal]:
        """No code supplied: no coupon, no discount, existing behaviour
        completely unchanged. Otherwise validates through CouponService --
        `for_update=True` locks the row and is used only at actual order
        placement; preview always uses the unlocked, read-only path."""
        if not coupon_code:
            return None, ZERO

        if for_update:
            return await self.coupons.lock_and_validate(coupon_code, subtotal, self.customer_id)
        return await self.coupons.validate_and_calculate(coupon_code, subtotal, self.customer_id)

    async def _summary(
        self,
        items: list[CheckoutItem],
        subtotal: Decimal,
        coupon: Coupon | None = None,
        discount: Decimal = ZERO,
    ) -> CheckoutPreview:
        """Total the basket: goods minus any coupon discount, then delivery,
        then tax on the discounted goods + delivery, then the total. This is
        the one place that formula lives -- preview and place_order both
        call it, so their numbers can never disagree."""
        discounted_subtotal = subtotal - discount
        shipping = await self.shipping.calculate(subtotal)
        tax = await self.tax.calculate(discounted_subtotal, shipping)

        return CheckoutPreview(
            items=items,
            subtotal=subtotal,
            coupon_code=coupon.code if coupon else None,
            discount_amount=discount,
            shipping_amount=shipping,
            tax_amount=tax,
            total_amount=discounted_subtotal + shipping + tax,
        )

    async def _next_order_number(self) -> str:
        """ORD-100001, ORD-100002, ... straight from a Postgres sequence."""
        number = await self.session.scalar(select(ORDER_NUMBER_SEQUENCE.next_value()))
        return f"{ORDER_NUMBER_PREFIX}{number}"


class OrderService:
    """Reading orders back and moving them through fulfilment, scoped to one tenant."""

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
        """Fetch one of the customer's own orders; anything else reads as not found."""
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
        """Move an order to its next status, adjusting stock and payment to match."""
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
        """Cancel the customer's own order, allowed only before PROCESSING."""
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
        """Mark the COD payment PAID; `update_status` owns the transaction."""
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
