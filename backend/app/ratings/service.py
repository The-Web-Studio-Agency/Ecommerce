from typing import List, Tuple
from fastapi import HTTPException, status

from app.ratings.models import Review, ReviewImage
from app.ratings.repository import ReviewRepository
from app.ratings.schemas import ReviewCreate, ReviewUpdate, RatingSummaryResponse


class ReviewService:
    def __init__(self, repository: ReviewRepository):
        self.repository = repository

    def create_review(self, user_id: int, tenant_id: str, data: ReviewCreate) -> Review:
        # Enforce that the user must have purchased the product and it must be delivered
        is_verified = self.repository.check_user_purchased_product(user_id, data.product_id)
        if not is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only review products that have been delivered to you."
            )

        # Check if user already reviewed this product
        existing_reviews, _ = self.repository.get_product_reviews(data.product_id, skip=0, limit=100)
        if any(r.user_id == user_id for r in existing_reviews):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already submitted a review for this product."
            )

        review = Review(
            tenant_id=tenant_id,
            product_id=data.product_id,
            user_id=user_id,
            rating=data.rating,
            title=data.title,
            comment=data.comment,
            is_verified_purchase=True,
            is_approved=True
        )

        images = [
            ReviewImage(image_url=img.image_url, alt_text=img.alt_text)
            for img in (data.images or [])
        ]

        return self.repository.create(review, images)

    def list_product_reviews(self, product_id: int, page: int = 1, size: int = 10) -> Tuple[List[Review], int]:
        skip = (page - 1) * size
        return self.repository.get_product_reviews(product_id, skip=skip, limit=size)

    def get_summary(self, product_id: int) -> RatingSummaryResponse:
        avg, total, distribution = self.repository.get_rating_summary(product_id)
        return RatingSummaryResponse(
            product_id=product_id,
            average_rating=avg,
            total_reviews=total,
            rating_distribution=distribution
        )

    def update_review(self, review_id: int, user_id: int, data: ReviewUpdate) -> Review:
        review = self.repository.get_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found.")
        if review.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to edit this review.")

        if data.rating is not None:
            review.rating = data.rating
        if data.title is not None:
            review.title = data.title
        if data.comment is not None:
            review.comment = data.comment
        if data.is_approved is not None:
            review.is_approved = data.is_approved

        return self.repository.update(review)

    def delete_review(self, review_id: int, user_id: int) -> None:
        review = self.repository.get_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found.")
        
        # Strict rule: Only the customer who wrote it can delete it. Admins cannot touch it.
        if review.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this review.")
        
        self.repository.delete(review)
