from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        UniqueConstraint("user_id", "product_id", name="uq_user_product_review"),
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            name="fk_reviews_tenant_product_products",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["users.tenant_id", "users.id"],
            name="fk_reviews_tenant_user_users",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            name="fk_reviews_tenant_order_orders",
            ondelete="SET NULL",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified_purchase: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_approved: Mapped[bool] = mapped_column(nullable=False, default=True)

    # Relationships
    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews", overlaps="product")
    order = relationship("Order", back_populates="reviews", overlaps="product,user")
    images: Mapped[List[ReviewImage]] = relationship(
        "ReviewImage", back_populates="review", cascade="all, delete-orphan"
    )


class ReviewImage(Base, TimestampMixin):
    __tablename__ = "review_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    review = relationship("Review", back_populates="images")