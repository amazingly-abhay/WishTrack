"""add_wishlists_table

Revision ID: a1b2c3d4e5f6
Revises: 454acb30d34c
Create Date: 2026-10-19 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import app.db.base

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '454acb30d34c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create wishlists table
    op.create_table(
        'wishlists',
        sa.Column('id', app.db.base.GUID(), nullable=False),
        sa.Column('user_id', app.db.base.GUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_wishlists_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_wishlists'))
    )
    op.create_index('ix_wishlists_user_created', 'wishlists', ['user_id', 'created_at'], unique=False)

    # 2. Add wishlist_id column to wishlist_items using batch mode for SQLite compatibility
    with op.batch_alter_table('wishlist_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('wishlist_id', app.db.base.GUID(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f('fk_wishlist_items_wishlist_id_wishlists'),
            'wishlists',
            ['wishlist_id'], ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index('ix_wishlist_items_wishlist_id', ['wishlist_id'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('wishlist_items', schema=None) as batch_op:
        batch_op.drop_index('ix_wishlist_items_wishlist_id')
        batch_op.drop_constraint(batch_op.f('fk_wishlist_items_wishlist_id_wishlists'), type_='foreignkey')
        batch_op.drop_column('wishlist_id')
    op.drop_index('ix_wishlists_user_created', table_name='wishlists')
    op.drop_table('wishlists')
