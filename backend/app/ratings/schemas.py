from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ReviewImageBase(BaseModel):
    image_url: str
    alt_text: Optional[str] = None


class ReviewImageCreate(ReviewImageBase):
    pass


class ReviewImageResponse(ReviewImageBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=150)
    comment: Optional[str] = Field(None, max_length=2000)
    images: Optional[List[ReviewImageCreate]] = []


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=150)
    comment: Optional[str] = Field(None, max_length=2000)
    is_approved: Optional[bool] = None


class ReviewResponse(BaseModel):
    id: int
    tenant_id: str
    product_id: int
    user_id: int
    order_id: Optional[int] = None
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    is_verified_purchase: bool
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    images: List[ReviewImageResponse] = []

    class Config:
        from_attributes = True


class RatingSummaryResponse(BaseModel):
    product_id: int
    average_rating: float
    total_reviews: int
    rating_distribution: dict[int, int]  # e.g., {1: count, 2: count, ... 5: count}