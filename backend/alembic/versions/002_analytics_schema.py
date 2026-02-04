"""Add analytics tracking schema

Revision ID: 002
Revises: 001_initial
Create Date: 2026-01-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Analytics Events table
    op.create_table(
        'analytics_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('event_name', sa.String(255)),
        sa.Column('session_id', sa.String(255), nullable=False, index=True),
        sa.Column('visitor_id', sa.String(255), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), index=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, index=True),
        sa.Column('client_timestamp', sa.BigInteger),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('path', sa.String(1024), nullable=False, index=True),
        sa.Column('referrer', sa.String(2048)),
        sa.Column('referrer_domain', sa.String(255), index=True),
        sa.Column('utm_source', sa.String(255), index=True),
        sa.Column('utm_medium', sa.String(255), index=True),
        sa.Column('utm_campaign', sa.String(255), index=True),
        sa.Column('utm_term', sa.String(255)),
        sa.Column('utm_content', sa.String(255)),
        sa.Column('device_type', sa.String(50)),
        sa.Column('browser', sa.String(100)),
        sa.Column('browser_version', sa.String(50)),
        sa.Column('os', sa.String(100)),
        sa.Column('os_version', sa.String(50)),
        sa.Column('country_code', sa.String(2), index=True),
        sa.Column('country_name', sa.String(100)),
        sa.Column('region', sa.String(100)),
        sa.Column('city', sa.String(100)),
        sa.Column('timezone', sa.String(100)),
        sa.Column('ip_address_hash', sa.String(64)),
        sa.Column('viewport_width', sa.Integer),
        sa.Column('viewport_height', sa.Integer),
        sa.Column('screen_width', sa.Integer),
        sa.Column('screen_height', sa.Integer),
        sa.Column('performance_data', postgresql.JSONB),
        sa.Column('ecommerce_data', postgresql.JSONB),
        sa.Column('properties', postgresql.JSONB),
        sa.Column('is_bot', sa.Boolean, default=False, index=True),
        sa.Column('consent_given', sa.Boolean, default=True),
        sa.Column('anonymized', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    # Create composite indexes for common query patterns
    op.create_index(
        'idx_events_timestamp_path',
        'analytics_events',
        ['timestamp', 'path']
    )
    op.create_index(
        'idx_events_session_timestamp',
        'analytics_events',
        ['session_id', 'timestamp']
    )
    op.create_index(
        'idx_events_visitor_timestamp',
        'analytics_events',
        ['visitor_id', 'timestamp']
    )
    op.create_index(
        'idx_events_type_timestamp',
        'analytics_events',
        ['event_type', 'timestamp']
    )

    # Analytics Sessions table
    op.create_table(
        'analytics_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('visitor_id', sa.String(255), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), index=True),
        sa.Column('start_time', sa.DateTime, nullable=False, index=True),
        sa.Column('end_time', sa.DateTime, nullable=False),
        sa.Column('duration_seconds', sa.Integer),
        sa.Column('entry_page', sa.String(1024)),
        sa.Column('exit_page', sa.String(1024)),
        sa.Column('pageview_count', sa.Integer, default=0),
        sa.Column('event_count', sa.Integer, default=0),
        sa.Column('click_count', sa.Integer, default=0),
        sa.Column('scroll_depth_avg', sa.Float),
        sa.Column('initial_referrer', sa.String(2048)),
        sa.Column('initial_utm_source', sa.String(255)),
        sa.Column('initial_utm_medium', sa.String(255)),
        sa.Column('initial_utm_campaign', sa.String(255)),
        sa.Column('device_type', sa.String(50)),
        sa.Column('browser', sa.String(100)),
        sa.Column('os', sa.String(100)),
        sa.Column('country_code', sa.String(2), index=True),
        sa.Column('has_conversion', sa.Boolean, default=False, index=True),
        sa.Column('conversion_value', sa.Float),
        sa.Column('is_bounce', sa.Boolean, default=False, index=True),
        sa.Column('has_rage_click', sa.Boolean, default=False),
        sa.Column('has_error', sa.Boolean, default=False),
        sa.Column('quality_score', sa.Float),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )

    op.create_index(
        'idx_sessions_visitor_start',
        'analytics_sessions',
        ['visitor_id', 'start_time']
    )
    op.create_index(
        'idx_sessions_conversion',
        'analytics_sessions',
        ['has_conversion', 'start_time']
    )

    # Conversion Funnels table
    op.create_table(
        'conversion_funnels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000)),
        sa.Column('steps', postgresql.JSONB, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('time_window_hours', sa.Integer, default=24),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )

    # Conversion Events table
    op.create_table(
        'conversion_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.String(255), nullable=False, index=True),
        sa.Column('visitor_id', sa.String(255), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), index=True),
        sa.Column('conversion_type', sa.String(100), nullable=False, index=True),
        sa.Column('conversion_value', sa.Float),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('first_touch_source', sa.String(255)),
        sa.Column('first_touch_medium', sa.String(255)),
        sa.Column('first_touch_campaign', sa.String(255)),
        sa.Column('last_touch_source', sa.String(255)),
        sa.Column('last_touch_medium', sa.String(255)),
        sa.Column('last_touch_campaign', sa.String(255)),
        sa.Column('touchpoint_count', sa.Integer),
        sa.Column('time_to_conversion_hours', sa.Float),
        sa.Column('order_id', sa.String(255), index=True),
        sa.Column('product_ids', postgresql.JSONB),
        sa.Column('timestamp', sa.DateTime, nullable=False, index=True),
        sa.Column('created_at', sa.DateTime),
    )

    op.create_index(
        'idx_conversions_timestamp_type',
        'conversion_events',
        ['timestamp', 'conversion_type']
    )

    # Session Replays table
    op.create_table(
        'session_replays',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('visitor_id', sa.String(255), nullable=False, index=True),
        sa.Column('duration_ms', sa.Integer),
        sa.Column('event_count', sa.Integer),
        sa.Column('storage_path', sa.String(1024)),
        sa.Column('compressed_size_bytes', sa.Integer),
        sa.Column('has_console_logs', sa.Boolean, default=False),
        sa.Column('has_network_data', sa.Boolean, default=False),
        sa.Column('privacy_mode', sa.String(50), default='strict'),
        sa.Column('has_errors', sa.Boolean, default=False),
        sa.Column('has_rage_clicks', sa.Boolean, default=False),
        sa.Column('quality_score', sa.Float),
        sa.Column('processing_status', sa.String(50), default='pending'),
        sa.Column('recorded_at', sa.DateTime, nullable=False, index=True),
        sa.Column('expires_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime),
    )

    # Heatmap Data table
    op.create_table(
        'heatmap_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('page_path', sa.String(1024), nullable=False, index=True),
        sa.Column('viewport_width', sa.Integer, nullable=False),
        sa.Column('click_map', postgresql.JSONB),
        sa.Column('scroll_map', postgresql.JSONB),
        sa.Column('move_map', postgresql.JSONB),
        sa.Column('attention_map', postgresql.JSONB),
        sa.Column('sample_size', sa.Integer),
        sa.Column('date_from', sa.DateTime, nullable=False),
        sa.Column('date_to', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )

    op.create_index(
        'idx_heatmap_page_viewport',
        'heatmap_data',
        ['page_path', 'viewport_width']
    )


def downgrade() -> None:
    op.drop_table('heatmap_data')
    op.drop_table('session_replays')
    op.drop_table('conversion_events')
    op.drop_table('conversion_funnels')
    op.drop_table('analytics_sessions')
    op.drop_table('analytics_events')
