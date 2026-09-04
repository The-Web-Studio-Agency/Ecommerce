from __future__ import annotations

import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.ratings.constants import ReviewArchiveReason, ReviewStatus


class Review(Base, TimestampMixin):
    """Customer review for a purchased product."""

    __tablename__ = "reviews"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_reviews_tenant_id_id",
        ),
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_reviews_rating_range",
        ),
        Index(
            "uq_tenant_user_product_review",
            "tenant_id",
            "user_id",
            "product_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "ix_reviews_tenant_id_product_id",
            "tenant_id",
            "product_id",
        ),
        Index(
            "ix_reviews_tenant_id_user_id",
            "tenant_id",
            "user_id",
        ),
        CheckConstraint(
            """
            (status = 'ACTIVE' AND archive_reason IS NULL)
            OR
            (status = 'ARCHIVED' AND archive_reason IS NOT NULL)
            """,
            name="ck_reviews_archive_reason_matches_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "products.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "orders.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_verified_purchase: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    is_approved: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    status: Mapped[ReviewStatus] = mapped_column(
        Enum(
            ReviewStatus,
            name="review_status",
        ),
        nullable=False,
        default=ReviewStatus.ACTIVE,
        server_default="ACTIVE",
    )

    archive_reason: Mapped[ReviewArchiveReason | None] = mapped_column(
        Enum(
            ReviewArchiveReason,
            name="review_archive_reason",
        ),
        nullable=True,
    )

    images: Mapped[list["ReviewImage"]] = relationship(
        "ReviewImage",
        primaryjoin=lambda: and_(
            Review.tenant_id == ReviewImage.tenant_id,
            Review.id == ReviewImage.review_id,
        ),
        foreign_keys=lambda: [
            ReviewImage.tenant_id,
            ReviewImage.review_id,
        ],
        back_populates="review",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReviewImage(Base, TimestampMixin):
    """Image attached to a review."""

    __tablename__ = "review_images"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_review_images_tenant_id_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "review_id",
            name="uq_review_images_one_per_review",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "review_id"],
            ["reviews.tenant_id", "reviews.id"],
            name="fk_review_images_tenant_review_reviews",
            ondelete="CASCADE",
        ),
        Index(
            "ix_review_images_tenant_id_review_id",
            "tenant_id",
            "review_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    alt_text: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    review: Mapped["Review"] = relationship(
        "Review",
        primaryjoin=lambda: and_(
            ReviewImage.tenant_id == Review.tenant_id,
            ReviewImage.review_id == Review.id,
        ),
        foreign_keys=lambda: [
            ReviewImage.tenant_id,
            ReviewImage.review_id,
        ],
        back_populates="images",
    )


class ProductRatingSummary(Base, TimestampMixin):
    """Maintained rating summary for a product."""

    __tablename__ = "product_rating_summaries"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "product_id",
            name="uq_product_rating_summaries_tenant_product",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    average_rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    total_reviews: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    rating_1_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    rating_2_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    rating_3_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    rating_4_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    rating_5_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )