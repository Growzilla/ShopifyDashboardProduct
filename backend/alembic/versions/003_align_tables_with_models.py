"""Align products, orders, insights tables with current SQLAlchemy models.

Migration 001 created these tables with UUID primary keys and different columns.
The models now use String(255) PKs (Shopify GIDs) for products/orders, and
insights has different columns (action_summary instead of description, etc.).

Since these tables have zero real data on production, we drop and recreate.

Revision ID: 003
Revises: 002
Create Date: 2026-02-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Drop old tables (no real data) ---
    op.drop_table('insights')
    op.drop_index('ix_orders_processed_at', table_name='orders')
    op.drop_table('orders')
    op.drop_table('products')

    # --- Recreate products (String PK = Shopify GID) ---
    op.create_table(
        'products',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('shops.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('handle', sa.String(255), index=True),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('product_type', sa.String(255), nullable=True),
        sa.Column('vendor', sa.String(255), nullable=True),
        sa.Column('total_inventory', sa.Integer(), server_default='0'),
        sa.Column('inventory_tracked', sa.Boolean(), server_default='true'),
        sa.Column('price_min', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('price_max', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('collections', postgresql.JSONB(), nullable=True),
        sa.Column('variants', postgresql.JSONB(), nullable=True),
        sa.Column('featured_image_url', sa.Text(), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Recreate orders (String PK = Shopify GID) ---
    op.create_table(
        'orders',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('shops.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('order_number', sa.Integer(), nullable=False, index=True),
        sa.Column('name', sa.String(50)),
        sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('subtotal_price', sa.Numeric(precision=12, scale=2), server_default='0'),
        sa.Column('total_tax', sa.Numeric(precision=12, scale=2), server_default='0'),
        sa.Column('total_discounts', sa.Numeric(precision=12, scale=2), server_default='0'),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('financial_status', sa.String(50), server_default='pending'),
        sa.Column('fulfillment_status', sa.String(50), nullable=True),
        sa.Column('customer_id', sa.String(255), nullable=True, index=True),
        sa.Column('customer_email', sa.String(255), nullable=True),
        sa.Column('line_items', postgresql.JSONB(), nullable=True),
        sa.Column('line_item_count', sa.Integer(), server_default='0'),
        sa.Column('discount_codes', postgresql.JSONB(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), index=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Recreate insights (matches current model) ---
    op.create_table(
        'insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('shops.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), server_default='medium'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('action_summary', sa.Text(), nullable=False),
        sa.Column('expected_uplift', sa.String(100), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='0.8'),
        sa.Column('payload', postgresql.JSONB(), nullable=True),
        sa.Column('admin_deep_link', sa.Text(), nullable=True),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actioned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Drop new-format tables
    op.drop_table('insights')
    op.drop_table('orders')
    op.drop_table('products')

    # Recreate old-format tables (from migration 001)
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('shops.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('shopify_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('handle', sa.String(255)),
        sa.Column('product_type', sa.String(255)),
        sa.Column('vendor', sa.String(255)),
        sa.Column('status', sa.String(50)),
        sa.Column('tags', postgresql.ARRAY(sa.String())),
        sa.Column('variants_count', sa.Integer(), server_default='0'),
        sa.Column('images_count', sa.Integer(), server_default='0'),
        sa.Column('total_inventory', sa.Integer(), server_default='0'),
        sa.Column('price_min', sa.Numeric(precision=10, scale=2)),
        sa.Column('price_max', sa.Numeric(precision=10, scale=2)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('shop_id', 'shopify_id', name='uq_products_shop_shopify_id'),
    )

    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('shops.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('shopify_id', sa.BigInteger(), nullable=False),
        sa.Column('order_number', sa.String(50)),
        sa.Column('email', sa.String(255)),
        sa.Column('financial_status', sa.String(50)),
        sa.Column('fulfillment_status', sa.String(50)),
        sa.Column('currency', sa.String(10)),
        sa.Column('total_price', sa.Numeric(precision=10, scale=2)),
        sa.Column('subtotal_price', sa.Numeric(precision=10, scale=2)),
        sa.Column('total_tax', sa.Numeric(precision=10, scale=2)),
        sa.Column('total_discounts', sa.Numeric(precision=10, scale=2)),
        sa.Column('line_items_count', sa.Integer(), server_default='0'),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('shop_id', 'shopify_id', name='uq_orders_shop_shopify_id'),
    )
    op.create_index('ix_orders_processed_at', 'orders', ['processed_at'])

    op.create_table(
        'insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('shops.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('recommendation', sa.Text()),
        sa.Column('metadata', postgresql.JSONB()),
        sa.Column('is_read', sa.Boolean(), server_default='false'),
        sa.Column('is_dismissed', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )
