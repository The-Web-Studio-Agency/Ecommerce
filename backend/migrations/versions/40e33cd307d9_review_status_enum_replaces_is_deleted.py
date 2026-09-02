"""review status enum replaces is_deleted

Revision ID: 40e33cd307d9
Revises: 1c2e5eb26f5c
Create Date: 2026-09-02 13:08:59.088513

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '40e33cd307d9'
down_revision: Union[str, Sequence[str], None] = '1c2e5eb26f5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


review_status_enum = postgresql.ENUM('ACTIVE', 'ARCHIVED', name='review_status')


def upgrade() -> None:
    """Upgrade schema."""
    # The old partial index's WHERE clause references is_deleted, which this
    # migration drops -- it has to go before that column does.
    op.drop_index('uq_tenant_user_product_review', table_name='reviews')

    review_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'reviews',
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'ARCHIVED', name='review_status', create_type=False),
            server_default='ACTIVE',
            nullable=False,
        ),
    )

    # Data migration: is_deleted=false -> ACTIVE (already the column default
    # above), is_deleted=true -> ARCHIVED.
    op.execute("UPDATE reviews SET status = 'ARCHIVED' WHERE is_deleted IS TRUE")

    op.drop_column('reviews', 'is_deleted')

    # Same unique guarantee as before, now keyed off status instead of is_deleted.
    op.create_index(
        'uq_tenant_user_product_review',
        'reviews',
        ['tenant_id', 'user_id', 'product_id'],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_tenant_user_product_review', table_name='reviews')

    op.add_column(
        'reviews',
        sa.Column(
            'is_deleted',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
    )

    op.execute("UPDATE reviews SET is_deleted = TRUE WHERE status = 'ARCHIVED'")

    op.drop_column('reviews', 'status')
    review_status_enum.drop(op.get_bind(), checkfirst=True)

    op.create_index(
        'uq_tenant_user_product_review',
        'reviews',
        ['tenant_id', 'user_id', 'product_id'],
        unique=True,
        postgresql_where=sa.text('NOT is_deleted'),
    )
