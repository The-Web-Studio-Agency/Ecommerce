import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.constants import UserRole, UserStatus
from app.models.base import Base, TimestampMixin

_ROLE_VALUES = ", ".join(f"'{role.value}'" for role in UserRole)
_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in UserStatus)

_E164_SQL = r"phone ~ '^\+[1-9][0-9]{7,14}$'"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    __table_args__ = (
        # Target for tenant-aware composite foreign keys from other modules
        # (carts, and orders later), matching the catalogue tables.
        UniqueConstraint("tenant_id", "id", name="uq_users_tenant_id_id"),
        UniqueConstraint("tenant_id", "phone", name="uq_users_tenant_phone"),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        CheckConstraint(f"role IN ({_ROLE_VALUES})", name="role_valid"),
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="status_valid"),
        CheckConstraint("email IS NULL OR email = lower(email)", name="email_is_lowercase"),
        CheckConstraint(_E164_SQL, name="phone_is_e164"),
        CheckConstraint(
            "(role = 'CUSTOMER') = (password_hash IS NULL)",
            name="password_matches_role",
        ),
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

    phone: Mapped[str] = mapped_column(String(16), nullable=False)

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.CUSTOMER.value,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserStatus.ACTIVE.value,
    )

    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
        overlaps="order,product,reviews",
    )
    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value
