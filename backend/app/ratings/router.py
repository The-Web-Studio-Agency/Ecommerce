from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import CurrentUser, require_admin
from app.tenants.resolver import CurrentTenant
from app.ratings.repository import ReviewRepository
from app.ratings.schemas import ReviewCreate, ReviewResponse, ReviewUpdate, RatingSummaryResponse
from app.ratings.service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Ratings & Reviews"])


def get_review_service(session: AsyncSession = Depends(get_db)) -> ReviewService:
    repo = ReviewRepository(session)
    return ReviewService(repo)


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    data: ReviewCreate,
    current_user: CurrentUser,
    tenant: CurrentTenant,
    service: ReviewService = Depends(get_review_service)
):
    return await service.create_review(user_id=current_user.id, tenant_id=tenant.id, data=data)


@router.get("/product/{product_id}", response_model=List[ReviewResponse])
async def get_product_reviews(
    product_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    service: ReviewService = Depends(get_review_service)
):
    reviews, _ = await service.list_product_reviews(product_id, page=page, size=size)
    return reviews


@router.get("/product/{product_id}/summary", response_model=RatingSummaryResponse)
async def get_product_rating_summary(
    product_id: UUID,
    service: ReviewService = Depends(get_review_service)
):
    return await service.get_summary(product_id)


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    data: ReviewUpdate,
    current_user: CurrentUser,
    service: ReviewService = Depends(get_review_service)
):
    return await service.update_review(review_id=review_id, user_id=current_user.id, data=data)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    current_user: CurrentUser,
    service: ReviewService = Depends(get_review_service)
):
    await service.delete_review(review_id=review_id, user_id=current_user.id)