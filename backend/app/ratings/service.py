from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.catalogue.service import ProductService
from app.ratings.constants import ReviewArchiveReason, ReviewStatus
from app.ratings.models import Review, ReviewImage
from app.ratings.repository import ReviewRepository
from app.ratings.schemas import (
    RatingSummaryResponse,
    ReviewCreate,
    ReviewUpdate,
)


class ReviewService:
    def __init__(self, repository: ReviewRepository):
        self.repository = repository

    async def create_review(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: ReviewCreate,
    ) -> Review:
        order_id = await self.repository.get_delivered_order_id(
            user_id,
            data.product_id,
            tenant_id,
        )

        if not order_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only review products you have purchased and received.",
            )

        existing_review = await self.repository.get_by_user_and_product(
            tenant_id,
            user_id,
            data.product_id,
        )

        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this product.",
            )

        review = Review(
            tenant_id=tenant_id,
            product_id=data.product_id,
            user_id=user_id,
            order_id=order_id,
            rating=data.rating,
            title=data.title,
            comment=data.comment,
            is_verified_purchase=True,
            is_approved=True,
            status=ReviewStatus.ACTIVE,
        )

        images = [
            ReviewImage(
                tenant_id=tenant_id,
                review=review,
                image_url=image.image_url,
                alt_text=image.alt_text,
            )
            for image in data.images
        ]

        review = await self.repository.create(
            review,
            images,
        )

        await self.repository.refresh_rating_summary(
            data.product_id,
            tenant_id,
        )

        return review

    async def list_product_reviews(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[Review], int]:
        product_service = ProductService(
            self.repository.session,
            tenant_id,
        )

        await product_service.get_public(product_id)

        reviews, total = await self.repository.get_product_reviews(
            product_id,
            tenant_id,
            skip,
            limit,
        )

        return reviews, total

    async def get_summary(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> RatingSummaryResponse:
        product_service = ProductService(
            self.repository.session,
            tenant_id,
        )

        await product_service.get_public(product_id)

        summary = await self.repository.get_maintained_summary(
            product_id,
            tenant_id,
        )

        if not summary:
            return RatingSummaryResponse(
                product_id=product_id,
                average_rating=0.0,
                total_reviews=0,
                rating_distribution={
                    1: 0,
                    2: 0,
                    3: 0,
                    4: 0,
                    5: 0,
                },
            )

        return RatingSummaryResponse(
            product_id=product_id,
            average_rating=summary.average_rating,
            total_reviews=summary.total_reviews,
            rating_distribution={
                1: summary.rating_1_count,
                2: summary.rating_2_count,
                3: summary.rating_3_count,
                4: summary.rating_4_count,
                5: summary.rating_5_count,
            },
        )

    async def list_admin_product_reviews(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[Review]:
        product_service = ProductService(
            self.repository.session,
            tenant_id,
        )

        await product_service.get(product_id)

        return await self.repository.get_admin_product_reviews(
            product_id,
            tenant_id,
        )

    async def get_admin_summary(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> RatingSummaryResponse:
        product_service = ProductService(
            self.repository.session,
            tenant_id,
        )

        await product_service.get(product_id)

        summary = await self.repository.get_maintained_summary(
            product_id,
            tenant_id,
        )

        if not summary:
            return RatingSummaryResponse(
                product_id=product_id,
                average_rating=0.0,
                total_reviews=0,
                rating_distribution={
                    1: 0,
                    2: 0,
                    3: 0,
                    4: 0,
                    5: 0,
                },
            )

        return RatingSummaryResponse(
            product_id=product_id,
            average_rating=summary.average_rating,
            total_reviews=summary.total_reviews,
            rating_distribution={
                1: summary.rating_1_count,
                2: summary.rating_2_count,
                3: summary.rating_3_count,
                4: summary.rating_4_count,
                5: summary.rating_5_count,
            },
        )

    async def update_review(
        self,
        review_id: uuid.UUID,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: ReviewUpdate,
    ) -> Review:
        review = await self.repository.get_by_id(
            review_id,
            tenant_id,
        )

        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found.",
            )

        if review.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own review.",
            )

        rating_changed = (
            data.rating is not None
            and data.rating != review.rating
        )

        if data.rating is not None:
            review.rating = data.rating

        if data.title is not None:
            review.title = data.title

        if data.comment is not None:
            review.comment = data.comment

        if data.images is not None:
            image = (
                ReviewImage(
                    tenant_id=tenant_id,
                    review_id=review.id,
                    image_url=data.images[0].image_url,
                    alt_text=data.images[0].alt_text,
                )
                if data.images
                else None
            )

            await self.repository.replace_review_image(
                review.id,
                tenant_id,
                image,
            )

        review = await self.repository.update(review)

        if rating_changed:
            await self.repository.refresh_rating_summary(
                review.product_id,
                tenant_id,
            )

        return review

    async def delete_review(
        self,
        review_id: uuid.UUID,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        review = await self.repository.get_by_id(
            review_id,
            tenant_id,
        )

        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found.",
            )

        if review.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own review.",
            )

        review.status = ReviewStatus.ARCHIVED
        review.archive_reason = ReviewArchiveReason.CUSTOMER_DELETED

        await self.repository.update(review)

        await self.repository.refresh_rating_summary(
            review.product_id,
            tenant_id,
        )