from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_customer, require_staff
from app.core import rate_limit
from app.core.config import get_settings
from app.core.database import get_db
from app.core.pagination import PageParams
from app.core.responses import ApiResponse, ok, paginated
from app.ratings.schemas import (
    RatingSummaryRead,
    ReviewCreate,
    ReviewModerate,
    ReviewModerationQuery,
    ReviewRead,
    ReviewUpdate,
)
from app.ratings.service import ReviewService
from app.tenants.resolver import CurrentTenant
from app.users.models import User

router = APIRouter(prefix="/reviews", tags=["Ratings & Reviews"])

admin_router = APIRouter(prefix="/admin/reviews", tags=["Admin-Review_moderation"])


@router.post(
    "",
    response_model=ApiResponse[ReviewRead],
    status_code=status.HTTP_201_CREATED,
    summary="Review a delivered product",
)
async def create_review(
    data: ReviewCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[ReviewRead]:
    settings = get_settings()
    await rate_limit.enforce(
        "review-create",
        str(user.tenant_id),
        str(user.id),
        limit=settings.review_rate_limit_attempts,
        window_seconds=settings.commerce_rate_limit_window_seconds,
    )

    review = await ReviewService(session, user.tenant_id).create(user.id, data)
    return ok(ReviewRead.model_validate(review), message="Review created")


@router.get(
    "/product/{product_id}",
    response_model=ApiResponse[list[ReviewRead]],
    summary="List approved reviews for a product",
)
async def list_product_reviews(
    product_id: UUID,
    tenant: CurrentTenant,
    params: Annotated[PageParams, Query()],
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ReviewRead]]:
    reviews, total = await ReviewService(session, tenant.id).list_for_product(
        product_id, params
    )
    return paginated(
        [ReviewRead.model_validate(review) for review in reviews],
        total_items=total,
        params=params,
        message="Reviews retrieved",
    )


@router.get(
    "/product/{product_id}/summary",
    response_model=ApiResponse[RatingSummaryRead],
    summary="Average rating and star distribution for a product",
)
async def get_product_rating_summary(
    product_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[RatingSummaryRead]:
    summary = await ReviewService(session, tenant.id).summary(product_id)
    return ok(summary, message="Rating summary retrieved")


@router.patch(
    "/{review_id}",
    response_model=ApiResponse[ReviewRead],
    summary="Edit your own review",
)
async def update_review(
    review_id: UUID,
    data: ReviewUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[ReviewRead]:
    review = await ReviewService(session, user.tenant_id).update(review_id, user.id, data)
    return ok(ReviewRead.model_validate(review), message="Review updated")


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete your own review",
)
async def delete_review(
    review_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> Response:
    await ReviewService(session, user.tenant_id).delete(review_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get(
    "",
    response_model=ApiResponse[list[ReviewRead]],
    summary="List reviews for moderation",
)
async def list_reviews_for_moderation(
    params: Annotated[ReviewModerationQuery, Query()],
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[list[ReviewRead]]:
    reviews, total = await ReviewService(session, user.tenant_id).list_for_moderation(
        params, is_approved=params.is_approved
    )
    return paginated(
        [ReviewRead.model_validate(review) for review in reviews],
        total_items=total,
        params=params,
        message="Reviews retrieved",
    )


@admin_router.get(
    "/product/{product_id}",
    response_model=ApiResponse[list[ReviewRead]],
    summary="List every review on a product, hidden ones included",
)
async def list_product_reviews_for_moderation(
    product_id: UUID,
    params: Annotated[PageParams, Query()],
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[list[ReviewRead]]:
    reviews, total = await ReviewService(session, user.tenant_id).list_for_product(
        product_id, params, approved_only=False
    )
    return paginated(
        [ReviewRead.model_validate(review) for review in reviews],
        total_items=total,
        params=params,
        message="Reviews retrieved",
    )


@admin_router.get(
    "/product/{product_id}/summary",
    response_model=ApiResponse[RatingSummaryRead],
    summary="Rating summary counting hidden reviews too",
)
async def get_product_rating_summary_for_moderation(
    product_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[RatingSummaryRead]:
    summary = await ReviewService(session, user.tenant_id).summary(
        product_id, approved_only=False
    )
    return ok(summary, message="Rating summary retrieved")


@admin_router.patch(
    "/{review_id}",
    response_model=ApiResponse[ReviewRead],
    summary="Approve or hide a review",
)
async def moderate_review(
    review_id: UUID,
    data: ReviewModerate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[ReviewRead]:
    review = await ReviewService(session, user.tenant_id).moderate(review_id, data)
    return ok(ReviewRead.model_validate(review), message="Review moderated")
