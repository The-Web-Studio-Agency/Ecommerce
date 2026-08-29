import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.tenants.constants import CURRENCY_CODE_LENGTH, DEFAULT_CURRENCY


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    __table_args__ = (
        # ISO 4217, upper case. Checked here so a lower-case "inr" cannot reach
        # a price label anywhere in the API.
        CheckConstraint(
            f"currency = upper(currency) AND length(currency) = {CURRENCY_CODE_LENGTH}",
            name="currency_is_iso_4217",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # What this storefront prices and collects in. Zeen sells in India, so
    # INR -- but a tenant in another market carries its own, which is why this
    # is a column rather than a constant.
    currency: Mapped[str] = mapped_column(
        String(CURRENCY_CODE_LENGTH),
        nullable=False,
        default=DEFAULT_CURRENCY,
        server_default=text(f"'{DEFAULT_CURRENCY}'"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )


class TenantDomain(Base, TimestampMixin):
    __tablename__ = "tenant_domains"

    __table_args__ = (
        CheckConstraint("domain = lower(domain)", name="domain_is_lowercase"),
        CheckConstraint("length(trim(domain)) > 0", name="domain_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    domain: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
