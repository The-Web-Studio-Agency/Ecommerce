import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.orders.models import Order, OrderItem
from app.ratings.models import Review, ReviewImage



class ReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, review_id: uuid.UUID) -> Optional[Review]:
        stmt = (
            select(Review)
            .options(selectinload(Review.images))
            .filter(Review.id == review_id)
        )
        result = await self.session.scalars(stmt)
        return result.first()

    async def get_product_reviews(
        self, product_id: uuid.UUID, skip: int = 0, limit: int = 10
    ) -> Tuple[List[Review], int]:
        base_query = select(Review).filter(
            Review.product_id == product_id, Review.is_approved == True
        )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = await self.session.scalar(count_stmt) or 0

        stmt = (
            base_query.options(selectinload(Review.images))
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        reviews = list(result.all())
        return reviews, total

    async def check_user_purchased_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> bool:
        stmt = (
            select(Order.id)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(
                Order.customer_id == user_id,
                OrderItem.product_id == product_id,
                Order.status == "delivered"
            )
            .limit(1)
        )
        return await self.session.scalar(stmt) is not None

    async def get_rating_summary(self, product_id: uuid.UUID) -> Tuple[float, int, dict[int, int]]:
        stmt = select(Review.rating, func.count(Review.id)).filter(
            Review.product_id == product_id, Review.is_approved == True
        ).group_by(Review.rating)

        result = await self.session.execute(stmt)
        results = result.all()
        distribution = {i: 0 for i in range(1, 6)}
        total_reviews = 0
        total_score = 0

        for rating, count in results:
            distribution[rating] = count
            total_reviews += count
            total_score += rating * count

        avg_rating = round(total_score / total_reviews, 2) if total_reviews > 0 else 0.0
        return avg_rating, total_reviews, distribution

    async def create(self, review: Review, images: List[ReviewImage] = None) -> Review:
        self.session.add(review)
        await self.session.flush()
        if images:
            for img in images:
                img.review_id = review.id
                self.session.add(img)
        await self.session.commit()
        await self.session.refresh(review)
        return review

    async def update(self, review: Review) -> Review:
        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        return review

    async def delete(self, review: Review) -> None:
        await self.session.delete(review)
        await self.session.commit()