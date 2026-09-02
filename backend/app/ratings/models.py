from __future__ import annotations

import enum
import uuid
from sqlalchemy import Enum
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
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

class ReviewStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ReviewArchiveReason(str, enum.Enum):
    """Why an ARCHIVED review became archived. ACTIVE reviews always have
    archive_reason = NULL; ARCHIVED reviews always have one of these."""

    PRODUCT_ARCHIVED = "PRODUCT_ARCHIVED"
    CUSTOMER_DELETED = "CUSTOMER_DELETED"

class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_reviews_tenant_id_id"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        # Partial: only among reviews that haven't been (soft-)deleted, so a
        # customer who deletes their review can leave a new one later without
        # the old, now-hidden row blocking them at the database level.
        Index(
            "uq_tenant_user_product_review",
            "tenant_id",
            "user_id",
            "product_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),

        Index("ix_reviews_tenant_id_product_id", "tenant_id", "product_id"),
        Index("ix_reviews_tenant_id_user_id", "tenant_id", "user_id"),
        CheckConstraint(
            "(status = 'ACTIVE' AND archive_reason IS NULL) OR "
            "(status = 'ARCHIVED' AND archive_reason IS NOT NULL)",
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
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Single-column FK (not tenant-composite): a composite (tenant_id, product_id)
    # FK's ON DELETE SET NULL would null every column it lists, including
    # tenant_id -- which is NOT NULL, so the delete would fail outright.
    # product_id is a globally unique UUID, so this loses no real integrity
    # check; the tenant match is already enforced when the review is created.
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Same reasoning as product_id above.
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Same reasoning as product_id above.
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified_purchase: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_approved: Mapped[bool] = mapped_column(nullable=False, default=True)

    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        nullable=False,
        default=ReviewStatus.ACTIVE,
        server_default=ReviewStatus.ACTIVE.value,
    )

    # NULL while ACTIVE; set to the reason the review was archived when
    # status becomes ARCHIVED (see ck_reviews_archive_reason_matches_status).
    archive_reason: Mapped[Optional[ReviewArchiveReason]] = mapped_column(
        Enum(ReviewArchiveReason, name="review_archive_reason"),
        nullable=True,
        default=None,
    )

    images: Mapped[List[ReviewImage]] = relationship(
        "ReviewImage",
        primaryjoin=lambda: and_(
            Review.id == ReviewImage.review_id,
            Review.tenant_id == ReviewImage.tenant_id,
        ),
        foreign_keys=lambda: [ReviewImage.review_id, ReviewImage.tenant_id],
        back_populates="review",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReviewImage(Base, TimestampMixin):
    __tablename__ = "review_images"

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_review_images_tenant_id_id"),
        # At most one image per review.
        UniqueConstraint(
            "tenant_id", "review_id", name="uq_review_images_one_per_review"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "review_id"],
            ["reviews.tenant_id", "reviews.id"],
            name="fk_review_images_tenant_review_reviews",
            ondelete="CASCADE",
        ),
        Index("ix_review_images_tenant_id_review_id", "tenant_id", "review_id"),
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
    )
    
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    review = relationship(
        "Review",
        primaryjoin=lambda: and_(
            ReviewImage.review_id == Review.id,
            ReviewImage.tenant_id == Review.tenant_id,
        ),
        foreign_keys=lambda: [ReviewImage.review_id, ReviewImage.tenant_id],
        back_populates="images",
    )




class ProductRatingSummary(Base, TimestampMixin):
    """Maintained rollup of a product's reviews.

    Recomputed and upserted whenever a review is created, edited, or
    (soft-)deleted, so reading a product's rating never costs an
    AVG/GROUP BY scan over its reviews.
    """

    __tablename__ = "product_rating_summaries"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "product_id", name="uq_product_rating_summaries_tenant_product"
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

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    average_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_1_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_2_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_3_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_4_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_5_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)