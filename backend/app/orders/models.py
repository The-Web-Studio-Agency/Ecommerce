import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    UniqueConstraint,
    and_,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.addresses.models import (
    MAX_CITY_LENGTH,
    MAX_LINE_LENGTH,
    MAX_NAME_LENGTH,
    MAX_POSTAL_CODE_LENGTH,
)
from app.catalogue.constants import (
    MAX_NAME_LENGTH as MAX_PRODUCT_NAME_LENGTH,
)
from app.catalogue.constants import (
    MAX_SKU_LENGTH,
    PRICE_PRECISION,
    PRICE_SCALE,
)
from app.models.base import Base, TimestampMixin
from app.orders.constants import (
    MAX_ORDER_NUMBER_LENGTH,
    ORDER_NUMBER_START,
    OrderStatus,
    PaymentStatus,
)
from app.payments.models import Payment

_ORDER_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in OrderStatus)
_PAYMENT_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in PaymentStatus)

# Customer-facing order numbers come from a Postgres sequence rather than a
# "select max() + 1", so two checkouts running at the same time can never be
# handed the same number. It is attached to the metadata, which means both
# Alembic and the test suite's create_all know to build it.
ORDER_NUMBER_SEQUENCE = Sequence(
    "order_number_seq", start=ORDER_NUMBER_START, metadata=Base.metadata
)


class Order(Base, TimestampMixin):
    """
    One placed order.

    Everything a customer needs to read this order back -- prices, product
    names, the delivery address -- is copied onto the order and its items when
    it is placed. Nothing here is looked up from the live catalogue, so a later
    price change or address edit cannot rewrite history.
    """

    __tablename__ = "orders"

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_orders_tenant_id_id"),
        UniqueConstraint("order_number", name="uq_orders_order_number"),
        ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["users.tenant_id", "users.id"],
            name="fk_orders_tenant_customer_users",
            ondelete="CASCADE",
        ),
        CheckConstraint(f"status IN ({_ORDER_STATUS_VALUES})", name="status_valid"),
        CheckConstraint(
            f"payment_status IN ({_PAYMENT_STATUS_VALUES})", name="payment_status_valid"
        ),
        CheckConstraint("subtotal >= 0", name="subtotal_not_negative"),
        CheckConstraint("shipping_amount >= 0", name="shipping_not_negative"),
        # The total is never stored independently of its parts, so a bug that
        # miscalculates one of them is a database error rather than a wrong
        # number on an invoice.
        CheckConstraint(
            "total_amount = subtotal + shipping_amount", name="total_is_subtotal_plus_shipping"
        ),
        Index("ix_orders_tenant_id_customer_id", "tenant_id", "customer_id"),
        Index("ix_orders_tenant_id_status", "tenant_id", "status"),
        Index("ix_orders_tenant_id_payment_status", "tenant_id", "payment_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # What the customer quotes at you on the phone. The UUID stays the primary
    # key; this is the identifier that appears in the API and in emails.
    order_number: Mapped[str] = mapped_column(
        String(MAX_ORDER_NUMBER_LENGTH), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OrderStatus.PENDING.value
    )

    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.PENDING.value
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )

    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )

    # ---- delivery address, copied from the customer's address at checkout ----

    delivery_name: Mapped[str] = mapped_column(String(MAX_NAME_LENGTH), nullable=False)

    delivery_phone: Mapped[str] = mapped_column(String(16), nullable=False)

    delivery_address_line_1: Mapped[str] = mapped_column(
        String(MAX_LINE_LENGTH), nullable=False
    )

    delivery_address_line_2: Mapped[str | None] = mapped_column(
        String(MAX_LINE_LENGTH), nullable=True
    )

    delivery_city: Mapped[str] = mapped_column(String(MAX_CITY_LENGTH), nullable=False)

    delivery_state: Mapped[str] = mapped_column(String(MAX_CITY_LENGTH), nullable=False)

    delivery_postal_code: Mapped[str] = mapped_column(
        String(MAX_POSTAL_CODE_LENGTH), nullable=False
    )

    delivery_country: Mapped[str] = mapped_column(
        String(MAX_CITY_LENGTH), nullable=False
    )

    # What is owed on this order and whether it has been collected. One
    # payment per order -- checkout writes it, and the status changes settle
    # it. Loaded the same way as the items, so reading an order never costs a
    # second round trip.
    payment: Mapped["Payment | None"] = relationship(
        "Payment",
        primaryjoin=lambda: and_(
            Order.id == Payment.order_id,
            Order.tenant_id == Payment.tenant_id,
        ),
        foreign_keys=lambda: [Payment.order_id, Payment.tenant_id],
        uselist=False,
        lazy="selectin",
        viewonly=True,
    )

    # selectin loading: one extra query per page of orders rather than one per
    # order, which is what keeps the order list off an N+1.
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        primaryjoin=lambda: and_(
            Order.id == OrderItem.order_id,
            Order.tenant_id == OrderItem.tenant_id,
        ),
        foreign_keys=lambda: [OrderItem.order_id, OrderItem.tenant_id],
        order_by=lambda: OrderItem.created_at,
        lazy="selectin",
        viewonly=True,
    )


class OrderItem(Base, TimestampMixin):
    """
    One line of an order, with the product details frozen at purchase time.

    product_id and variant_id are kept so an admin can still jump to the
    catalogue entry, but nothing in the response is read from them. If the
    product is renamed or repriced tomorrow, this row is unaffected.
    """

    __tablename__ = "order_items"

    __table_args__ = (
        # One line per variant per order -- the same variant twice would be a
        # checkout bug, not a legitimate order.
        UniqueConstraint("order_id", "variant_id", name="uq_order_items_order_variant"),
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            name="fk_order_items_tenant_order_orders",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "variant_id"],
            ["product_variants.tenant_id", "product_variants.id"],
            name="fk_order_items_tenant_variant_product_variants",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            name="fk_order_items_tenant_product_products",
            ondelete="CASCADE",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_not_negative"),
        CheckConstraint(
            "subtotal = unit_price * quantity", name="subtotal_is_price_times_quantity"
        ),
        Index("ix_order_items_tenant_id_order_id", "tenant_id", "order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ---- snapshot of the catalogue at the moment the order was placed ----

    product_name: Mapped[str] = mapped_column(
        String(MAX_PRODUCT_NAME_LENGTH), nullable=False
    )

    variant_name: Mapped[str] = mapped_column(
        String(MAX_PRODUCT_NAME_LENGTH), nullable=False
    )

    sku: Mapped[str] = mapped_column(String(MAX_SKU_LENGTH), nullable=False)

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )
