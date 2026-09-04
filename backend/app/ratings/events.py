from __future__ import annotations

from uuid import UUID

from sqlalchemy import event, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, attributes

from app.catalogue.constants import CatalogueStatus
from app.catalogue.models import Product
from app.ratings.constants import ReviewArchiveReason, ReviewStatus
from app.ratings.models import ProductRatingSummary, Review


_ACTIVE = CatalogueStatus.ACTIVE.value
_ARCHIVED = CatalogueStatus.ARCHIVED.value


def _archive_active_reviews(
    session: Session,
    tenant_id: UUID,
    product_id: UUID,
) -> None:
    reviews = session.execute(
        select(Review).filter(
            Review.tenant_id == tenant_id,
            Review.product_id == product_id,
            Review.status == ReviewStatus.ACTIVE,
        )
    ).scalars().all()

    for review in reviews:
        review.status = ReviewStatus.ARCHIVED
        review.archive_reason = ReviewArchiveReason.PRODUCT_ARCHIVED


def _restore_product_archived_reviews(
    session: Session,
    tenant_id: UUID,
    product_id: UUID,
) -> None:
    # Never touches ARCHIVED/CUSTOMER_DELETED reviews -- only ones archived
    # because the product itself was archived.
    reviews = session.execute(
        select(Review).filter(
            Review.tenant_id == tenant_id,
            Review.product_id == product_id,
            Review.status == ReviewStatus.ARCHIVED,
            Review.archive_reason == ReviewArchiveReason.PRODUCT_ARCHIVED,
        )
    ).scalars().all()

    for review in reviews:
        review.status = ReviewStatus.ACTIVE
        review.archive_reason = None


def _refresh_rating_summary(
    session: Session,
    tenant_id: UUID,
    product_id: UUID,
) -> None:
    """Refresh the maintained rating summary without committing."""

    reviews = session.execute(
        select(Review).filter(
            Review.tenant_id == tenant_id,
            Review.product_id == product_id,
        )
    ).scalars().all()

    distribution = {i: 0 for i in range(1, 6)}
    total_reviews = 0
    total_score = 0

    for review in reviews:
        if review.status != ReviewStatus.ACTIVE or not review.is_approved:
            continue

        distribution[review.rating] += 1
        total_reviews += 1
        total_score += review.rating

    avg_rating = round(total_score / total_reviews, 2) if total_reviews else 0.0

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
        set_={
            key: value
            for key, value in values.items()
            if key not in ("tenant_id", "product_id")
        },
    )
    session.execute(stmt)


@event.listens_for(Session, "before_flush")
def sync_reviews_with_product_status(
    session: Session,
    flush_context,
    instances,
) -> None:
    for obj in list(session.dirty):
        if not isinstance(obj, Product):
            continue

        history = attributes.get_history(obj, "status")

        # An empty `deleted` means there's no prior persisted value to
        # compare against (e.g. this is a brand new row) -- nothing to sync.
        if not history.added or not history.deleted:
            continue

        old_status, new_status = history.deleted[0], history.added[0]
        if old_status == new_status:
            continue

        if new_status == _ARCHIVED and old_status != _ARCHIVED:
            _archive_active_reviews(session, obj.tenant_id, obj.id)
            _refresh_rating_summary(session, obj.tenant_id, obj.id)
        elif new_status == _ACTIVE and old_status == _ARCHIVED:
            _restore_product_archived_reviews(session, obj.tenant_id, obj.id)
            _refresh_rating_summary(session, obj.tenant_id, obj.id)