import uuid

from typing import List, Optional, Tuple


from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.orders.models import Order, OrderItem
from app.ratings.models import (
    ProductRatingSummary,
    Review,
    ReviewArchiveReason,
    ReviewImage,
    ReviewStatus,
)
from app.orders.constants import OrderStatus

class ReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, review_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Review]:
        stmt = (
            select(Review)
            .options(selectinload(Review.images))
            .filter(
                Review.id == review_id,
                Review.tenant_id == tenant_id,
                Review.status == ReviewStatus.ACTIVE,
            )
        )
        result = await self.session.scalars(stmt)
        return result.first()

    async def get_by_user_and_product(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, product_id: uuid.UUID
    ) -> Optional[Review]:
        """Any review by this user for this product, approved or not, live or
        deleted -- used purely to check "have they already reviewed this",
        so it must not be filtered the way a public listing would be."""
        stmt = select(Review).filter(
            Review.tenant_id == tenant_id,
            Review.user_id == user_id,
            Review.product_id == product_id,
            Review.status == ReviewStatus.ACTIVE,
        )
        return await self.session.scalar(stmt)

    async def get_product_reviews(
        self, product_id: uuid.UUID, tenant_id: uuid.UUID, skip: int = 0, limit: int = 10
    ) -> Tuple[List[Review], int]:
        base_query = select(Review).filter(
            Review.tenant_id == tenant_id,
            Review.product_id == product_id,
            Review.is_approved == True,
            Review.status == ReviewStatus.ACTIVE,
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

    async def get_delivered_order_id(
        self, user_id: uuid.UUID, product_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[uuid.UUID]:
        """The order this purchase was delivered on, if any -- also lets the
        review record which order it came from (see Review.order_id)."""
        stmt = (
            select(Order.id)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(
                Order.tenant_id == tenant_id,
                Order.customer_id == user_id,
                OrderItem.product_id == product_id,
                Order.status == OrderStatus.DELIVERED,
            )
            .order_by(Order.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def get_rating_summary(
        self, product_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Tuple[float, int, dict[int, int]]:
        stmt = select(Review.rating, func.count(Review.id)).filter(
            Review.tenant_id == tenant_id,
            Review.product_id == product_id,
            Review.is_approved == True,
            Review.status == ReviewStatus.ACTIVE,
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

    async def get_maintained_summary(
        self, product_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[ProductRatingSummary]:
        stmt = select(ProductRatingSummary).filter(
            ProductRatingSummary.tenant_id == tenant_id,
            ProductRatingSummary.product_id == product_id,
        )
        return await self.session.scalar(stmt)

    async def refresh_rating_summary(self, product_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Recompute and upsert the maintained aggregate for one product.

        Called after every review create/update/(soft-)delete so summary
        reads never need to scan and aggregate the reviews table themselves.
        """
        avg_rating, total_reviews, distribution = await self.get_rating_summary(product_id, tenant_id)

        values = dict(
            tenant_id=tenant_id,
            product_id=product_id,
            average_rating=avg_rating,
            total_reviews=total_reviews,
            rating_1_count=distribution[1],
            rating_2_count=distribution[2],
            rating_3_count=distribution[3],
            rating_4_count=distribution[4],
            rating_5_count=distribution[5],
        )

        stmt = pg_insert(ProductRatingSummary).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "product_id"],
            set_={k: v for k, v in values.items() if k not in ("tenant_id", "product_id")},
        )
        await self.session.execute(stmt)
        await self.session.commit()

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
        await self.session.commit()
        # Commit expires every attribute, not just images -- restricting the
        # refresh to attribute_names=["images"] leaves updated_at (and
        # everything else) expired, so serializing the response later tries
        # to lazy-load it outside the async context and raises MissingGreenlet.
        await self.session.refresh(review)
        return review

    async def replace_review_image(
        self,
        review_id: uuid.UUID,
        tenant_id: uuid.UUID,
        image: Optional[ReviewImage],
    ) -> None:
        stmt = select(ReviewImage).filter(
            ReviewImage.review_id == review_id,
            ReviewImage.tenant_id == tenant_id,
        )

        result = await self.session.scalars(stmt)
        existing_image = result.first()

        if existing_image is not None:
            await self.session.delete(existing_image)
            # Without this, SQLAlchemy can emit the new image's INSERT before
            # this DELETE within the same flush (no dependency links them,
            # different rows) and collide with uq_review_images_one_per_review.
            await self.session.flush()

        if image is not None:
            image.review_id = review_id
            image.tenant_id = tenant_id
            self.session.add(image)
    
    async def get_admin_product_reviews(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 10,
    ) -> Tuple[List[Review], int]:

        base_query = select(Review).filter(
            Review.tenant_id == tenant_id,
            Review.product_id == product_id,
        )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = await self.session.scalar(count_stmt) or 0

        stmt = (
            base_query
            .options(selectinload(Review.images))
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.scalars(stmt)
        reviews = list(result.all())

        return reviews, total

    async def archive_active_reviews_for_product(
        self, product_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[Review]:
        """ACTIVE -> ARCHIVED/PRODUCT_ARCHIVED for every currently-active
        review of this product. Never touches reviews already archived for
        another reason (e.g. CUSTOMER_DELETED)."""
        stmt = select(Review).filter(
            Review.tenant_id == tenant_id,
            Review.product_id == product_id,
            Review.status == ReviewStatus.ACTIVE,
        )
        result = await self.session.scalars(stmt)
        reviews = list(result.all())
        for review in reviews:
            review.status = ReviewStatus.ARCHIVED
            review.archive_reason = ReviewArchiveReason.PRODUCT_ARCHIVED
        return reviews

    async def restore_product_archived_reviews_for_product(
        self, product_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[Review]:
        """ARCHIVED/PRODUCT_ARCHIVED -> ACTIVE/NULL for this product. Reviews
        archived because the customer deleted them (CUSTOMER_DELETED) are
        never restored here."""
        stmt = select(Review).filter(
            Review.tenant_id == tenant_id,
            Review.product_id == product_id,
            Review.status == ReviewStatus.ARCHIVED,
            Review.archive_reason == ReviewArchiveReason.PRODUCT_ARCHIVED,
        )
        result = await self.session.scalars(stmt)
        reviews = list(result.all())
        for review in reviews:
            review.status = ReviewStatus.ACTIVE
            review.archive_reason = None
        return reviews