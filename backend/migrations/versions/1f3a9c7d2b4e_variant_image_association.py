"""variant image association

Revision ID: 1f3a9c7d2b4e
Revises: 27f827e24c4a
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f3a9c7d2b4e'
down_revision: Union[str, Sequence[str], None] = '27f827e24c4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The new composite FK below points at (tenant_id, id) on product_images;
    # like every other tenant-scoped composite FK in this schema, the target
    # needs its own unique constraint on exactly those two columns first.
    op.create_unique_constraint(
        'uq_product_images_tenant_id_id', 'product_images', ['tenant_id', 'id']
    )

    op.add_column(
        'product_variants', sa.Column('image_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_product_variants_tenant_image_product_images',
        'product_variants',
        'product_images',
        ['tenant_id', 'image_id'],
        ['tenant_id', 'id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_product_variants_tenant_image_product_images',
        'product_variants',
        type_='foreignkey',
    )
    op.drop_column('product_variants', 'image_id')
    op.drop_constraint(
        'uq_product_images_tenant_id_id', 'product_images', type_='unique'
    )
