"""Automatic review lifecycle sync with product archive/reactivate.

Catalogue files must not be modified, so this listens for Product.status
transitions at the ORM level instead of catalogue code calling into ratings
explicitly. Registered by importing this module once from
app.models.registry (see that file).

A SQLAlchemy `before_flush` event fires on the plain (sync) `Session` even
when the app uses `AsyncSession` -- greenlet bridges the call -- so this runs
synchronously in the SAME flush/transaction as the product status change
that triggered it: no second commit, no window where product and reviews
disagree, no reliance on a caller remembering to call the ratings service.
"""

from __future__ import annotations

from sqlalchemy import event, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, attributes

from app.catalogue.constants import CatalogueStatus
from app.catalogue.models import Product
from app.ratings.models import (
    ProductRatingSummary,
    Review,
    ReviewArchiveReason,
    ReviewStatus,
)

_ACTIVE = CatalogueStatus.ACTIVE.value
_ARCHIVED = CatalogueStatus.ARCHIVED.value


def _archive_active_reviews(session: Session, tenant_id, product_id) -> None:
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


def _restore_product_archived_reviews(session: Session, tenant_id, product_id) -> None:
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


def _refresh_rating_summary(session: Session, tenant_id, product_id) -> None:
    """Sync counterpart of ReviewRepository.refresh_rating_summary, without
    the commit -- the outer flush this listener runs inside owns that.

    Deliberately does not filter by status/is_approved in SQL: the
    archive/restore above only changed Python-side attributes on
    already-loaded Review objects, and those UPDATEs haven't reached the
    database yet (still inside before_flush). A WHERE clause would evaluate
    against the stale pre-flush row and miss the pending change. Selecting
    every review for the product and filtering here in Python instead reads
    off the identity map's live objects, so the aggregate reflects the
    transition that's about to be flushed.
    """
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
        set_={k: v for k, v in values.items() if k not in ("tenant_id", "product_id")},
    )
    session.execute(stmt)


@event.listens_for(Session, "before_flush")
def sync_reviews_with_product_status(session: Session, flush_context, instances) -> None:
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
