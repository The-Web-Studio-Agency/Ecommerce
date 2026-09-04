from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.ratings.constants import ReviewArchiveReason, ReviewStatus


class ReviewImageBase(BaseModel):
    image_url: str
    alt_text: str | None = None


class ReviewImageCreate(ReviewImageBase):
    pass


class ReviewImageResponse(ReviewImageBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class ReviewCreate(BaseModel):
    product_id: uuid.UUID

    rating: int = Field(
        ...,
        ge=1,
        le=5,
    )

    title: str | None = None
    comment: str | None = None

    images: list[ReviewImageCreate] = Field(
        default_factory=list,
        max_length=1,
    )


class ReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int | None = Field(
        None,
        ge=1,
        le=5,
    )

    title: str | None = None
    comment: str | None = None

    images: list[ReviewImageCreate] | None = Field(
        None,
        max_length=1,
    )


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: uuid.UUID | None
    user_id: uuid.UUID | None
    order_id: uuid.UUID | None

    rating: int
    title: str | None
    comment: str | None

    is_verified_purchase: bool
    is_approved: bool

    status: ReviewStatus
    archive_reason: ReviewArchiveReason | None

    created_at: datetime
    updated_at: datetime

    images: list[ReviewImageResponse] = Field(
        default_factory=list,
    )


class RatingSummaryResponse(BaseModel):
    product_id: uuid.UUID
    average_rating: float
    total_reviews: int
    rating_distribution: dict[int, int]