import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.catalogue.constants import PRICE_PRECISION, PRICE_SCALE
from app.models.base import Base, TimestampMixin
from app.payments.constants import PaymentProvider, PaymentStatus

_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in PaymentStatus)
_PROVIDER_VALUES = ", ".join(f"'{provider.value}'" for provider in PaymentProvider)


class Payment(Base, TimestampMixin):
    """
    What is owed on one order, and whether it has been collected.

    Exactly one per order, written by checkout. Cash on delivery, so it is
    PENDING from the moment the order is placed until the courier hands the
    goods over and takes the money -- PAID once the order is delivered, FAILED
    if it is cancelled first. Nothing else ever writes one, and a partial
    unique index makes a second PAID row for the same order impossible even if
    something tried.

    The amount is copied from the order. It is never read from the request, so
    what the customer owes cannot be influenced by the browser.
    """

    __tablename__ = "payments"

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_payments_tenant_id_id"),
        # A payment cannot point at an order in another tenant.
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            name="fk_payments_tenant_order_orders",
            ondelete="CASCADE",
        ),
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="status_valid"),
        CheckConstraint(f"provider IN ({_PROVIDER_VALUES})", name="provider_valid"),
        CheckConstraint("amount >= 0", name="amount_not_negative"),
        # "An order is paid once" lives in the database, so two deliveries
        # recorded at the same moment cannot both collect the cash.
        Index(
            "uq_payments_one_paid_per_order",
            "tenant_id",
            "order_id",
            unique=True,
            postgresql_where=text("status = 'PAID'"),
        ),
        Index("ix_payments_tenant_id_order_id", "tenant_id", "order_id"),
        Index("ix_payments_tenant_id_status", "tenant_id", "status"),
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

    amount: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.PENDING.value
    )

    provider: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentProvider.COD.value
    )
