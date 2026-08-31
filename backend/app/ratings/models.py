from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
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
        # Tenant-scoped unique constraint so a user can only review a product once per tenant
        UniqueConstraint("tenant_id", "user_id", "product_id", name="uq_tenant_user_product_review"),
        
        # Product foreign key: If a product is removed, set product_id to NULL (or handle gracefully) 
        # without destroying the review history if you prefer, or keep CASCADE if product hard-deletes are fine.
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            name="fk_reviews_tenant_product_products",
            ondelete="CASCADE",
        ),
        
        # User foreign key: When a user account is deleted, SET NULL keeps the review alive in the database
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["users.tenant_id", "users.id"],
            name="fk_reviews_tenant_user_users",
            ondelete="SET NULL",
        ),
        
        # Order foreign key: If an order is cleared, keep the review alive by setting order_id to NULL
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            name="fk_reviews_tenant_order_orders",
            ondelete="SET NULL",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Product ID stays required or can be adjusted depending on your soft-delete strategy
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    # MUST be nullable=True to support ondelete="SET NULL" when a user is deleted
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Must be nullable=True for ondelete="SET NULL"
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified_purchase: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_approved: Mapped[bool] = mapped_column(nullable=False, default=True)

    # Relationships (configured to avoid breaking deletes)
    product = relationship("Product", back_populates="reviews", lazy="selectin")
    user = relationship("User", back_populates="reviews", overlaps="product", lazy="selectin")
    order = relationship("Order", back_populates="reviews", overlaps="product,user", lazy="selectin")
    images: Mapped[List[ReviewImage]] = relationship(
        "ReviewImage", back_populates="review", cascade="all, delete-orphan", lazy="selectin"
    )


class ReviewImage(Base, TimestampMixin):
    __tablename__ = "review_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    review = relationship("Review", back_populates="images")