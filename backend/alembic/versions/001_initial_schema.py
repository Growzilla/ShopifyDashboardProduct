"""Initial schema with all models including code analysis.

Revision ID: 001_initial
Revises:
Create Date: 2024-12-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Shops table ###
    op.create_table(
        'shops',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('domain', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('deep_mode_enabled', sa.Boolean(), default=False),
        sa.Column('clarity_project_id', sa.String(255), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(50), default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ### Products table ###
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shops.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('shopify_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('handle', sa.String(255)),
        sa.Column('product_type', sa.String(255)),
        sa.Column('vendor', sa.String(255)),
        sa.Column('status', sa.String(50)),
        sa.Column('tags', postgresql.ARRAY(sa.String())),
        sa.Column('variants_count', sa.Integer(), default=0),
        sa.Column('images_count', sa.Integer(), default=0),
        sa.Column('total_inventory', sa.Integer(), default=0),
        sa.Column('price_min', sa.Numeric(precision=10, scale=2)),
        sa.Column('price_max', sa.Numeric(precision=10, scale=2)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('shop_id', 'shopify_id', name='uq_products_shop_shopify_id'),
    )

    # ### Orders table ###
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shops.id', ondelete='CASCADE'), nullable=False, index=True),
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
        sa.Column('line_items_count', sa.Integer(), default=0),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('shop_id', 'shopify_id', name='uq_orders_shop_shopify_id'),
    )
    op.create_index('ix_orders_processed_at', 'orders', ['processed_at'])

    # ### Insights table ###
    op.create_table(
        'insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shops.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('recommendation', sa.Text()),
        sa.Column('metadata', postgresql.JSONB()),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('is_dismissed', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # ### Code Submissions table ###
    op.create_table(
        'code_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shops.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('language', sa.String(50), default='python'),
        sa.Column('filename', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), default='pending', index=True),
        sa.Column('priority', sa.String(10), default='normal'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ### Analysis Results table ###
    op.create_table(
        'analysis_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('code_submissions.id', ondelete='CASCADE'), unique=True, index=True),
        sa.Column('bugs', postgresql.JSONB(), default=list),
        sa.Column('security_issues', postgresql.JSONB(), default=list),
        sa.Column('optimizations', postgresql.JSONB(), default=list),
        sa.Column('performance_suggestions', postgresql.JSONB(), default=list),
        sa.Column('performance_score', sa.Integer(), default=0),
        sa.Column('security_score', sa.Integer(), default=0),
        sa.Column('quality_score', sa.Integer(), default=0),
        sa.Column('overall_grade', sa.String(2), default='C'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('ai_model', sa.String(50), default='gpt-4-turbo-preview'),
        sa.Column('tokens_used', sa.Integer(), default=0),
        sa.Column('analysis_duration_ms', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ### Notification Preferences table ###
    op.create_table(
        'notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shops.id', ondelete='CASCADE'), unique=True, index=True),
        sa.Column('email_enabled', sa.Boolean(), default=True),
        sa.Column('email_address', sa.String(255), nullable=True),
        sa.Column('webhook_enabled', sa.Boolean(), default=False),
        sa.Column('webhook_url', sa.Text(), nullable=True),
        sa.Column('webhook_secret', sa.String(64), nullable=True),
        sa.Column('in_app_enabled', sa.Boolean(), default=True),
        sa.Column('notify_on_complete', sa.Boolean(), default=True),
        sa.Column('notify_on_critical', sa.Boolean(), default=True),
        sa.Column('notify_on_batch', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ### Traffic Metrics table ###
    op.create_table(
        'traffic_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('hour', sa.DateTime(timezone=True), unique=True, index=True),
        sa.Column('request_count', sa.Integer(), default=0),
        sa.Column('submission_count', sa.Integer(), default=0),
        sa.Column('analysis_count', sa.Integer(), default=0),
        sa.Column('avg_response_ms', sa.Integer(), default=0),
        sa.Column('error_count', sa.Integer(), default=0),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('traffic_metrics')
    op.drop_table('notification_preferences')
    op.drop_table('analysis_results')
    op.drop_table('code_submissions')
    op.drop_table('insights')
    op.drop_index('ix_orders_processed_at', 'orders')
    op.drop_table('orders')
    op.drop_table('products')
    op.drop_table('shops')
