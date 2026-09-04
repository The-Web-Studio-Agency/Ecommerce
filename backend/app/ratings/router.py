from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_staff
from app.core.database import get_db
from app.ratings.repository import ReviewRepository
from app.ratings.schemas import (
    RatingSummaryResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
)
from app.ratings.service import ReviewService
from app.tenants.resolver import CurrentTenant


router = APIRouter(prefix="/reviews", tags=["Reviews"])


def get_review_service(
    session: AsyncSession = Depends(get_db),
) -> ReviewService:
    repository = ReviewRepository(session)
    return ReviewService(repository)


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    data: ReviewCreate,
    current_user: CurrentUser,
    tenant: CurrentTenant,
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    return await service.create_review(
        current_user.id,
        tenant.id,
        data,
    )


@router.get(
    "/product/{product_id}",
    response_model=list[ReviewResponse],
)
async def list_product_reviews(
    product_id: UUID,
    tenant: CurrentTenant,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    service: ReviewService = Depends(get_review_service),
) -> list[ReviewResponse]:
    return await service.list_product_reviews(
        product_id,
        tenant.id,
        skip,
        limit,
    )


@router.get(
    "/product/{product_id}/summary",
    response_model=RatingSummaryResponse,
)
async def get_product_rating_summary(
    product_id: UUID,
    tenant: CurrentTenant,
    service: ReviewService = Depends(get_review_service),
) -> RatingSummaryResponse:
    return await service.get_summary(
        product_id,
        tenant.id,
    )


@router.get(
    "/admin/product/{product_id}",
    response_model=list[ReviewResponse],
)
async def list_admin_product_reviews(
    product_id: UUID,
    tenant: CurrentTenant,
    user=Depends(require_staff),
    service: ReviewService = Depends(get_review_service),
) -> list[ReviewResponse]:
    return await service.list_admin_product_reviews(
        product_id,
        tenant.id,
    )


@router.get(
    "/admin/product/{product_id}/summary",
    response_model=RatingSummaryResponse,
)
async def get_admin_product_rating_summary(
    product_id: UUID,
    tenant: CurrentTenant,
    user=Depends(require_staff),
    service: ReviewService = Depends(get_review_service),
) -> RatingSummaryResponse:
    return await service.get_admin_summary(
        product_id,
        tenant.id,
    )

@router.patch(
    "/{review_id}",
    response_model=ReviewResponse,
)
async def update_review(
    review_id: UUID,
    data: ReviewUpdate,
    current_user: CurrentUser,
    tenant: CurrentTenant,
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    return await service.update_review(
        review_id,
        current_user.id,
        tenant.id,
        data,
    )


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_review(
    review_id: UUID,
    current_user: CurrentUser,
    tenant: CurrentTenant,
    service: ReviewService = Depends(get_review_service),
) -> None:
    await service.delete_review(
        review_id,
        current_user.id,
        tenant.id,
    )