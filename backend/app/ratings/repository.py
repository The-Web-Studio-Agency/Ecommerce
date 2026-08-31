from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.orders.models import Order, OrderItem
from app.ratings.models import Review, ReviewImage



class ReviewRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, review_id: int) -> Optional[Review]:
        stmt = (
            select(Review)
            .options(selectinload(Review.images))
            .filter(Review.id == review_id)
        )
        return self.session.scalars(stmt).first()
    
    def get_product_reviews(
        self, product_id: int, skip: int = 0, limit: int = 10
    ) -> Tuple[List[Review], int]:
        base_query = select(Review).filter(
            Review.product_id == product_id, Review.is_approved == True
        )
        
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = self.session.scalar(count_stmt) or 0

        stmt = (
            base_query.options(selectinload(Review.images))
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        reviews = list(self.session.scalars(stmt).all())
        return reviews, total

    def check_user_purchased_product(self, user_id: int, product_id: int) -> bool:
        stmt = (
            select(Order.id)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(
                Order.user_id == user_id,
                OrderItem.product_id == product_id,
                Order.status == "delivered"
            )
            .limit(1)
        )
        return self.session.scalar(stmt) is not None

    def get_rating_summary(self, product_id: int) -> Tuple[float, int, dict[int, int]]:
        stmt = select(Review.rating, func.count(Review.id)).filter(
            Review.product_id == product_id, Review.is_approved == True
        ).group_by(Review.rating)
        
        results = self.session.execute(stmt).all()
        distribution = {i: 0 for i in range(1, 6)}
        total_reviews = 0
        total_score = 0

        for rating, count in results:
            distribution[rating] = count
            total_reviews += count
            total_score += rating * count

        avg_rating = round(total_score / total_reviews, 2) if total_reviews > 0 else 0.0
        return avg_rating, total_reviews, distribution

    def create(self, review: Review, images: List[ReviewImage] = None) -> Review:
        self.session.add(review)
        self.session.flush()
        if images:
            for img in images:
                img.review_id = review.id
                self.session.add(img)
        self.session.commit()
        self.session.refresh(review)
        return review

    def update(self, review: Review) -> Review:
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)
        return review

    def delete(self, review: Review) -> None:
        self.session.delete(review)
        self.session.commit()