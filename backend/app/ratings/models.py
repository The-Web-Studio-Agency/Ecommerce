from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_reviews_tenant_id_id"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        UniqueConstraint("tenant_id", "user_id", "product_id", name="uq_tenant_user_product_review"),
        
        # Product deletion: SET NULL preserves review history even if the product is deleted
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            name="fk_reviews_tenant_product_products",
            ondelete="SET NULL",
        ),
        
        # User deletion: SET NULL keeps the review alive
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["users.tenant_id", "users.id"],
            name="fk_reviews_tenant_user_users",
            ondelete="SET NULL",
        ),
        
        # Order deletion: SET NULL keeps the review alive
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            name="fk_reviews_tenant_order_orders",
            ondelete="SET NULL",
        ),
        Index("ix_reviews_tenant_id_product_id", "tenant_id", "product_id"),
        Index("ix_reviews_tenant_id_user_id", "tenant_id", "user_id"),
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
    
    # Nullable to support SET NULL when a product is deleted
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    
    # Nullable to support SET NULL when a user account is deleted
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    
    # Nullable to support SET NULL when an order is cleared
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified_purchase: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_approved: Mapped[bool] = mapped_column(nullable=False, default=True)

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