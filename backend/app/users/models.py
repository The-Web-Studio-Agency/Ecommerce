import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.constants import UserRole
from app.models.base import Base, TimestampMixin

_ROLE_VALUES = ", ".join(f"'{role.value}'" for role in UserRole)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    __table_args__ = (
        # Tenant users: one address per tenant.
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        # Platform users have tenant_id IS NULL, which the constraint above
        # cannot constrain (NULLs are never equal in a unique index), so their
        # uniqueness needs its own partial index.
        Index(
            "uq_users_platform_email",
            "email",
            unique=True,
            postgresql_where=text("tenant_id IS NULL"),
        ),
        # The application already restricts roles, but the column is a plain
        # string: without this the database would accept a typo or a role
        # invented by a future code path.
        CheckConstraint(f"role IN ({_ROLE_VALUES})", name="role_valid"),
        # A platform administrator sits above the tenant boundary and every
        # other role sits inside exactly one tenant. Without this, a
        # TENANT_ADMIN with no tenant - or a PLATFORM_ADMIN scoped to one - is
        # representable, and neither has defined authorization semantics.
        CheckConstraint(
            "(role = 'PLATFORM_ADMIN') = (tenant_id IS NULL)",
            name="role_matches_tenant_scope",
        ),
        # Emails are lowercased by the service before insert. Enforcing it here
        # is what makes the unique constraints above actually
        # case-insensitive: without it, 'A@b.com' and 'a@b.com' are two rows.
        CheckConstraint("email = lower(email)", name="email_is_lowercase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Nullable because platform-level users sit above the tenant boundary.
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.CUSTOMER.value,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
