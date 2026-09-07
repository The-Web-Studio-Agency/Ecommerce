from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.logging import get_logger
from app.core.pagination import PageParams
from app.ratings.constants import (
    ALREADY_REVIEWED,
    NOT_DELIVERED,
    NOT_REVIEW_AUTHOR,
    REVIEW_NOT_FOUND,
)
from app.ratings.models import Review, ReviewImage
from app.ratings.repository import ReviewRepository
from app.ratings.schemas import (
    RatingSummaryRead,
    ReviewCreate,
    ReviewModerate,
    ReviewUpdate,
)

logger = get_logger("ratings")


class ReviewService:
    """Product reviews. Only a delivered purchase earns one, and only one."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.reviews = ReviewRepository(session, tenant_id)

    async def create(self, customer_id: UUID, data: ReviewCreate) -> Review:
        order_id = await self.reviews.delivered_order_id(customer_id, data.product_id)
        if order_id is None:
            raise PermissionDeniedError(NOT_DELIVERED)

        if await self.reviews.get_by_author(data.product_id, customer_id) is not None:
            raise ConflictError(ALREADY_REVIEWED)

        review = Review(
            product_id=data.product_id,
            user_id=customer_id,
            order_id=order_id,
            rating=data.rating,
            title=data.title,
            comment=data.comment,
            is_verified_purchase=True,
            is_approved=True,
            images=[
                ReviewImage(
                    tenant_id=self.tenant_id,
                    image_url=image.image_url,
                    alt_text=image.alt_text,
                )
                for image in data.images
            ],
        )

        try:
            await self.reviews.add(review)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(ALREADY_REVIEWED) from exc

        logger.info(
            "ratings.review_created id=%s tenant_id=%s product_id=%s",
            review.id,
            self.tenant_id,
            review.product_id,
        )
        return review

    async def list_for_product(
        self, product_id: UUID, params: PageParams, *, approved_only: bool = True
    ) -> tuple[list[Review], int]:
        rows, total = await self.reviews.paginate(
            self.reviews.product_select(product_id, approved_only=approved_only),
            params,
        )
        return list(rows), total

    async def list_for_moderation(
        self, params: PageParams, *, is_approved: bool | None = None
    ) -> tuple[list[Review], int]:
        rows, total = await self.reviews.paginate(
            self.reviews.moderation_select(is_approved=is_approved), params
        )
        return list(rows), total

    async def summary(
        self, product_id: UUID, *, approved_only: bool = True
    ) -> RatingSummaryRead:
        counts = await self.reviews.rating_counts(
            product_id, approved_only=approved_only
        )

        total_reviews = sum(counts.values())
        total_score = sum(star * count for star, count in counts.items())
        average = round(total_score / total_reviews, 2) if total_reviews else 0.0

        return RatingSummaryRead(
            product_id=product_id,
            average_rating=average,
            total_reviews=total_reviews,
            rating_distribution=counts,
        )

    async def update(
        self, review_id: UUID, customer_id: UUID, data: ReviewUpdate
    ) -> Review:
        review = await self._owned_by(review_id, customer_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(review, field, value)

        await self.session.commit()
        return review

    async def moderate(self, review_id: UUID, data: ReviewModerate) -> Review:
        review = await self._get(review_id)
        review.is_approved = data.is_approved

        await self.session.commit()
        logger.info(
            "ratings.review_moderated id=%s tenant_id=%s is_approved=%s",
            review.id,
            self.tenant_id,
            review.is_approved,
        )
        return review

    async def delete(self, review_id: UUID, customer_id: UUID) -> None:
        review = await self._owned_by(review_id, customer_id)

        await self.reviews.delete(review)
        await self.session.commit()

    async def _get(self, review_id: UUID) -> Review:
        review = await self.reviews.get(review_id)
        if review is None:
            raise NotFoundError(REVIEW_NOT_FOUND)
        return review

    async def _owned_by(self, review_id: UUID, customer_id: UUID) -> Review:
        review = await self._get(review_id)
        if review.user_id != customer_id:
            raise PermissionDeniedError(NOT_REVIEW_AUTHOR)
        return review
