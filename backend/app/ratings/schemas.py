import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl
from pydantic import ConfigDict
from app.ratings.models import ReviewArchiveReason, ReviewStatus

class ReviewImageBase(BaseModel):
    image_url: str
    alt_text: Optional[str] = None


class ReviewImageCreate(ReviewImageBase):
    pass


class ReviewImageResponse(ReviewImageBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    product_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=150)
    comment: Optional[str] = Field(None, max_length=2000)
    # At most one image per review.
    images: Optional[List[ReviewImageCreate]] = Field(default_factory=list, max_length=1)


class ReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=150)
    comment: Optional[str] = Field(None, max_length=2000)
    # is_approved is deliberately absent: it's moderation state, not
    # something a customer can set on their own review.
    images: Optional[List[ReviewImageCreate]] = Field(None, max_length=1)

class ReviewResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    status: ReviewStatus
    archive_reason: Optional[ReviewArchiveReason] = None
    is_verified_purchase: bool
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    images: List[ReviewImageResponse] = []

    class Config:
        from_attributes = True


class RatingSummaryResponse(BaseModel):
    product_id: uuid.UUID
    average_rating: float
    total_reviews: int
    rating_distribution: dict[int, int]