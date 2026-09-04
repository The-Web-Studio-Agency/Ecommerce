from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.ratings.constants import (
    MAX_ALT_TEXT_LENGTH,
    MAX_COMMENT_LENGTH,
    MAX_IMAGE_URL_LENGTH,
    MAX_IMAGES_PER_REVIEW,
    MAX_RATING,
    MAX_TITLE_LENGTH,
    MIN_RATING,
)


class ReviewImageCreate(BaseModel):
    image_url: str = Field(max_length=MAX_IMAGE_URL_LENGTH)
    alt_text: str | None = Field(default=None, max_length=MAX_ALT_TEXT_LENGTH)


class ReviewImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_url: str
    alt_text: str | None = None
    created_at: datetime


class ReviewCreate(BaseModel):
    product_id: uuid.UUID
    rating: int = Field(ge=MIN_RATING, le=MAX_RATING)
    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)
    comment: str | None = Field(default=None, max_length=MAX_COMMENT_LENGTH)
    images: list[ReviewImageCreate] = Field(
        default_factory=list, max_length=MAX_IMAGES_PER_REVIEW
    )


class ReviewUpdate(BaseModel):
    """What an author may change. Approval is a moderator's call, not theirs."""

    rating: int | None = Field(default=None, ge=MIN_RATING, le=MAX_RATING)
    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)
    comment: str | None = Field(default=None, max_length=MAX_COMMENT_LENGTH)


class ReviewModerate(BaseModel):
    is_approved: bool


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    rating: int
    title: str | None = None
    comment: str | None = None
    is_verified_purchase: bool
    is_approved: bool
    created_at: datetime
    images: list[ReviewImageRead] = Field(default_factory=list)


class RatingSummaryRead(BaseModel):
    product_id: uuid.UUID
    average_rating: float
    total_reviews: int
    rating_distribution: dict[int, int]
