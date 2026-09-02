import uuid
from typing import List, Tuple
from fastapi import HTTPException, status

from app.ratings.models import Review, ReviewArchiveReason, ReviewImage, ReviewStatus
from app.ratings.repository import ReviewRepository
from app.ratings.schemas import ReviewCreate, ReviewUpdate, RatingSummaryResponse
from app.catalogue.service import ProductService

class ReviewService:
    def __init__(self, repository: ReviewRepository):
        self.repository = repository

    async def create_review(self, user_id: uuid.UUID, tenant_id: uuid.UUID, data: ReviewCreate) -> Review:
        delivered_order_id = await self.repository.get_delivered_order_id(
            user_id, data.product_id, tenant_id
        )
        if delivered_order_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only review products that have been delivered to you."
            )

        # Checked directly rather than through the public listing (which only
        # shows approved, non-deleted reviews) -- an unapproved or otherwise
        # hidden existing review must still block a duplicate, or the
        # database's own unique constraint would reject it with a raw 500
        # instead of a clean, explained 400.
        existing = await self.repository.get_by_user_and_product(tenant_id, user_id, data.product_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already submitted a review for this product."
            )

        review = Review(
            tenant_id=tenant_id,
            product_id=data.product_id,
            user_id=user_id,
            order_id=delivered_order_id,
            rating=data.rating,
            title=data.title,
            comment=data.comment,
            is_verified_purchase=True,
            is_approved=True
        )

        images = [
            ReviewImage(tenant_id=tenant_id, image_url=img.image_url, alt_text=img.alt_text)
            for img in (data.images or [])
        ]

        created = await self.repository.create(review, images)
        await self.repository.refresh_rating_summary(data.product_id, tenant_id)
        return created

    async def list_product_reviews(
        self, product_id: uuid.UUID, tenant_id: uuid.UUID, page: int = 1, size: int = 10
    ) -> Tuple[List[Review], int]:
        # Public users can only see reviews for publicly visible products.
        product_service = ProductService(self.repository.session, tenant_id)
        await product_service.get_public(product_id)

        skip = (page - 1) * size

        return await self.repository.get_product_reviews(
            product_id,
            tenant_id,
            skip=skip,
            limit=size
        )
    async def get_summary(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> RatingSummaryResponse:

        # Public users can only see summaries for publicly visible products.
        product_service = ProductService(self.repository.session, tenant_id)
        await product_service.get_public(product_id)

        summary = await self.repository.get_maintained_summary(
            product_id,
            tenant_id
        )

        if summary is None:
            return RatingSummaryResponse(
                product_id=product_id,
                average_rating=0.0,
                total_reviews=0,
                rating_distribution={i: 0 for i in range(1, 6)},
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
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[Review], int]:
        # Admin/staff can view reviews for active or archived products.
        product_service = ProductService(self.repository.session, tenant_id)
        await product_service.get(product_id)

        skip = (page - 1) * size

        return await self.repository.get_admin_product_reviews(
            product_id,
            tenant_id,
            skip=skip,
            limit=size,
        )


    async def get_admin_summary(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> RatingSummaryResponse:
        # Admin/staff can view the summary for active or archived products.
        product_service = ProductService(self.repository.session, tenant_id)
        await product_service.get(product_id)

        summary = await self.repository.get_maintained_summary(
            product_id,
            tenant_id,
        )

        if summary is None:
            return RatingSummaryResponse(
                product_id=product_id,
                average_rating=0.0,
                total_reviews=0,
                rating_distribution={i: 0 for i in range(1, 6)},
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
        review = await self.repository.get_by_id(review_id, tenant_id)

        if not review:
            raise HTTPException(
                status_code=404,
                detail="Review not found.",
            )

        if review.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to edit this review.",
            )

        rating_changed = (
            data.rating is not None
            and data.rating != review.rating
        )

        # Update rating
        if data.rating is not None:
            review.rating = data.rating

        # Update title
        if data.title is not None:
            review.title = data.title

        # Update comment
        if data.comment is not None:
            review.comment = data.comment

        # Update image only when the client explicitly sends "images"
        if data.images is not None:
            image = None

            if data.images:
                image_data = data.images[0]

                image = ReviewImage(
                    tenant_id=tenant_id,
                    review_id=review.id,
                    image_url=image_data.image_url,
                    alt_text=image_data.alt_text,
                )

            await self.repository.replace_review_image(
                review_id=review.id,
                tenant_id=tenant_id,
                image=image,
            )

        updated = await self.repository.update(review)

        # Rating summary only needs refreshing if rating changed.
        if rating_changed:
            await self.repository.refresh_rating_summary(
                review.product_id,
                tenant_id,
            )

        return updated

    async def delete_review(self, review_id: uuid.UUID, user_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        review = await self.repository.get_by_id(review_id, tenant_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found.")

        if review.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this review.")

        # Soft delete: the review is hidden from listings and no longer
        # counted, but the row survives for rating history, and the unique
        # (tenant, user, product) slot frees up for a fresh review later.
        review.status = ReviewStatus.ARCHIVED
        review.archive_reason = ReviewArchiveReason.CUSTOMER_DELETED

        await self.repository.update(review)

        await self.repository.refresh_rating_summary(
            review.product_id,
            tenant_id,
        )