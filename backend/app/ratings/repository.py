from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.orders.constants import OrderStatus
from app.orders.models import Order, OrderItem
from app.ratings.constants import ReviewArchiveReason, ReviewStatus
from app.ratings.models import (
    ProductRatingSummary,
    Review,
    ReviewImage,
)


class ReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self,
        review_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Review | None:
        return await self.session.scalar(
            select(Review)
            .options(selectinload(Review.images))
            .filter(
                Review.id == review_id,
                Review.tenant_id == tenant_id,
                Review.status == ReviewStatus.ACTIVE,
            )
        )

    async def get_by_user_and_product(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> Review | None:
        return await self.session.scalar(
            select(Review).filter(
                Review.tenant_id == tenant_id,
                Review.user_id == user_id,
                Review.product_id == product_id,
                Review.status == ReviewStatus.ACTIVE,
            )
        )

    async def get_product_reviews(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[Review], int]:
        count_query = select(func.count()).select_from(Review).filter(
            Review.tenant_id == tenant_id,
            Review.product_id == product_id,
            Review.status == ReviewStatus.ACTIVE,
            Review.is_approved.is_(True),
        )

        total = await self.session.scalar(count_query) or 0

        query = (
            select(Review)
            .options(selectinload(Review.images))
            .filter(
                Review.tenant_id == tenant_id,
                Review.product_id == product_id,
                Review.status == ReviewStatus.ACTIVE,
                Review.is_approved.is_(True),
            )
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        reviews = list((await self.session.scalars(query)).all())

        return reviews, total

    async def get_delivered_order_id(
        self,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> uuid.UUID | None:
        query = (
            select(Order.id)
            .join(
                OrderItem,
                OrderItem.order_id == Order.id,
            )
            .filter(
                Order.tenant_id == tenant_id,
                Order.user_id == user_id,
                Order.status == OrderStatus.DELIVERED,
                OrderItem.product_id == product_id,
            )
            .order_by(Order.created_at.desc())
            .limit(1)
        )

        return await self.session.scalar(query)

    async def get_rating_summary(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict:
        query = (
            select(
                func.avg(Review.rating),
                func.count(Review.id),
                Review.rating,
            )
            .filter(
                Review.tenant_id == tenant_id,
                Review.product_id == product_id,
                Review.status == ReviewStatus.ACTIVE,
                Review.is_approved.is_(True),
            )
            .group_by(Review.rating)
        )

        rows = (await self.session.execute(query)).all()

        distribution = {i: 0 for i in range(1, 6)}
        total_reviews = 0
        total_score = 0

        for average, count, rating in rows:
            distribution[rating] = count
            total_reviews += count
            total_score += rating * count

        return {
            "average_rating": (
                round(total_score / total_reviews, 2)
                if total_reviews
                else 0.0
            ),
            "total_reviews": total_reviews,
            "rating_distribution": distribution,
        }

    async def get_maintained_summary(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ProductRatingSummary | None:
        return await self.session.scalar(
            select(ProductRatingSummary).filter(
                ProductRatingSummary.tenant_id == tenant_id,
                ProductRatingSummary.product_id == product_id,
            )
        )

    async def refresh_rating_summary(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        summary = await self.get_rating_summary(
            product_id,
            tenant_id,
        )

        values = {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "average_rating": summary["average_rating"],
            "total_reviews": summary["total_reviews"],
            "rating_1_count": summary["rating_distribution"][1],
            "rating_2_count": summary["rating_distribution"][2],
            "rating_3_count": summary["rating_distribution"][3],
            "rating_4_count": summary["rating_distribution"][4],
            "rating_5_count": summary["rating_distribution"][5],
        }

        stmt = pg_insert(ProductRatingSummary).values(**values)

        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "tenant_id",
                "product_id",
            ],
            set_={
                key: value
                for key, value in values.items()
                if key not in {
                    "tenant_id",
                    "product_id",
                }
            },
        )

        await self.session.execute(stmt)
        await self.session.commit()

    async def create(
        self,
        review: Review,
        images: list[ReviewImage] | None = None,
    ) -> Review:
        self.session.add(review)
        await self.session.flush()

        if images:
            self.session.add_all(images)

        await self.session.commit()
        await self.session.refresh(review)

        return review

    async def update(self, review: Review) -> Review:
        await self.session.commit()
        await self.session.refresh(review)

        return review

    async def replace_review_image(
        self,
        review_id: uuid.UUID,
        tenant_id: uuid.UUID,
        image: ReviewImage | None,
    ) -> None:
        existing_image = await self.session.scalar(
            select(ReviewImage).filter(
                ReviewImage.tenant_id == tenant_id,
                ReviewImage.review_id == review_id,
            )
        )

        if existing_image:
            await self.session.delete(existing_image)
            await self.session.flush()

        if image:
            self.session.add(image)

    async def get_admin_product_reviews(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[Review]:
        query = (
            select(Review)
            .options(selectinload(Review.images))
            .filter(
                Review.tenant_id == tenant_id,
                Review.product_id == product_id,
            )
            .order_by(Review.created_at.desc())
        )

        return list((await self.session.scalars(query)).all())

    async def archive_active_reviews_for_product(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        reviews = (
            await self.session.scalars(
                select(Review).filter(
                    Review.tenant_id == tenant_id,
                    Review.product_id == product_id,
                    Review.status == ReviewStatus.ACTIVE,
                )
            )
        ).all()

        for review in reviews:
            review.status = ReviewStatus.ARCHIVED
            review.archive_reason = ReviewArchiveReason.PRODUCT_ARCHIVED

    async def restore_product_archived_reviews_for_product(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        reviews = (
            await self.session.scalars(
                select(Review).filter(
                    Review.tenant_id == tenant_id,
                    Review.product_id == product_id,
                    Review.status == ReviewStatus.ARCHIVED,
                    Review.archive_reason
                    == ReviewArchiveReason.PRODUCT_ARCHIVED,
                )
            )
        ).all()

        for review in reviews:
            review.status = ReviewStatus.ACTIVE
            review.archive_reason = None