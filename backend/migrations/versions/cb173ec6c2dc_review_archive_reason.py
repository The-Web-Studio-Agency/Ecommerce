"""review archive reason

Revision ID: cb173ec6c2dc
Revises: 40e33cd307d9
Create Date: 2026-09-02 14:19:57.122566

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cb173ec6c2dc'
down_revision: Union[str, Sequence[str], None] = '40e33cd307d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


review_archive_reason_enum = postgresql.ENUM(
    'PRODUCT_ARCHIVED', 'CUSTOMER_DELETED', name='review_archive_reason'
)


def upgrade() -> None:
    """Upgrade schema."""
    review_archive_reason_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'reviews',
        sa.Column(
            'archive_reason',
            sa.Enum('PRODUCT_ARCHIVED', 'CUSTOMER_DELETED', name='review_archive_reason', create_type=False),
            nullable=True,
        ),
    )

    # Backfill: every pre-existing ARCHIVED row got there through the old
    # is_deleted=true path, which was always a customer's own deletion --
    # PRODUCT_ARCHIVED via automatic sync didn't exist before this migration.
    op.execute(
        "UPDATE reviews SET archive_reason = 'CUSTOMER_DELETED' WHERE status = 'ARCHIVED'"
    )

    op.create_check_constraint(
        'ck_reviews_archive_reason_matches_status',
        'reviews',
        "(status = 'ACTIVE' AND archive_reason IS NULL) OR "
        "(status = 'ARCHIVED' AND archive_reason IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_reviews_archive_reason_matches_status', 'reviews', type_='check')
    op.drop_column('reviews', 'archive_reason')
    review_archive_reason_enum.drop(op.get_bind(), checkfirst=True)
