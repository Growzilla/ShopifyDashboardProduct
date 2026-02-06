"""
Analytics data models for tracking web traffic and user behavior.

==============================================================================
MVP STATUS: DISABLED - These models are not imported in MVP.
The full analytics module is overengineered for initial launch.
Tables exist in DB but are not used. To re-enable: uncomment analytics router
==============================================================================
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    JSON,
    Index,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.core.database import Base


class AnalyticsEvent(Base):
    """
    Core analytics event model - stores all tracking events.
    Optimized for high-throughput writes and time-series queries.
    """

    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event identification
    event_type = Column(String(100), nullable=False, index=True)  # pageview, click, conversion, etc.
    event_name = Column(String(255))  # Custom event name

    # Session & User tracking (privacy-first)
    session_id = Column(String(255), nullable=False, index=True)
    visitor_id = Column(String(255), nullable=False, index=True)  # Fingerprint hash
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Authenticated user (optional)

    # Temporal data
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    client_timestamp = Column(BigInteger)  # Unix timestamp from client

    # Page context
    url = Column(String(2048), nullable=False)
    path = Column(String(1024), nullable=False, index=True)
    referrer = Column(String(2048))
    referrer_domain = Column(String(255), index=True)

    # Traffic source (UTM parameters)
    utm_source = Column(String(255), index=True)
    utm_medium = Column(String(255), index=True)
    utm_campaign = Column(String(255), index=True)
    utm_term = Column(String(255))
    utm_content = Column(String(255))

    # Device & Browser (from User-Agent)
    device_type = Column(String(50))  # desktop, mobile, tablet
    browser = Column(String(100))
    browser_version = Column(String(50))
    os = Column(String(100))
    os_version = Column(String(50))

    # Geographic data (from IP, anonymized)
    country_code = Column(String(2), index=True)
    country_name = Column(String(100))
    region = Column(String(100))
    city = Column(String(100))
    timezone = Column(String(100))

    # Network
    ip_address_hash = Column(String(64))  # SHA-256 hash for privacy

    # Viewport & Screen
    viewport_width = Column(Integer)
    viewport_height = Column(Integer)
    screen_width = Column(Integer)
    screen_height = Column(Integer)

    # Performance metrics (Web Vitals)
    performance_data = Column(JSONB)  # LCP, FID, CLS, TTFB, etc.

    # Ecommerce data
    ecommerce_data = Column(JSONB)  # cart_value, product_id, etc.

    # Custom properties
    properties = Column(JSONB)  # Flexible schema for custom tracking

    # Privacy & Compliance
    is_bot = Column(Boolean, default=False, index=True)
    consent_given = Column(Boolean, default=True)
    anonymized = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes for common query patterns
    __table_args__ = (
        Index("idx_events_timestamp_path", "timestamp", "path"),
        Index("idx_events_session_timestamp", "session_id", "timestamp"),
        Index("idx_events_visitor_timestamp", "visitor_id", "timestamp"),
        Index("idx_events_type_timestamp", "event_type", "timestamp"),
        Index("idx_events_ecommerce", "timestamp", postgresql_where=Column("ecommerce_data").isnot(None)),
    )


class AnalyticsSession(Base):
    """
    Session aggregation model - stores session-level metrics.
    Updated in real-time as events come in.
    """

    __tablename__ = "analytics_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    visitor_id = Column(String(255), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Session timing
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Integer)

    # Entry & Exit
    entry_page = Column(String(1024))
    exit_page = Column(String(1024))

    # Engagement metrics
    pageview_count = Column(Integer, default=0)
    event_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    scroll_depth_avg = Column(Float)  # Average across all pages

    # Traffic source
    initial_referrer = Column(String(2048))
    initial_utm_source = Column(String(255))
    initial_utm_medium = Column(String(255))
    initial_utm_campaign = Column(String(255))

    # Device context (from first event)
    device_type = Column(String(50))
    browser = Column(String(100))
    os = Column(String(100))
    country_code = Column(String(2), index=True)

    # Conversion tracking
    has_conversion = Column(Boolean, default=False, index=True)
    conversion_value = Column(Float)  # Total revenue in session

    # Behavior flags
    is_bounce = Column(Boolean, default=False, index=True)  # Single page, < 10s
    has_rage_click = Column(Boolean, default=False)  # Frustration indicator
    has_error = Column(Boolean, default=False)

    # Session quality score (ML-generated)
    quality_score = Column(Float)  # 0-100, likelihood of conversion

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_sessions_start_time", "start_time"),
        Index("idx_sessions_visitor_start", "visitor_id", "start_time"),
        Index("idx_sessions_conversion", "has_conversion", "start_time"),
    )


class ConversionFunnel(Base):
    """
    Conversion funnel configuration and tracking.
    """

    __tablename__ = "conversion_funnels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))

    # Funnel steps (ordered)
    steps = Column(JSONB, nullable=False)  # [{"name": "View Product", "url_pattern": "/products/*"}, ...]

    # Configuration
    is_active = Column(Boolean, default=True)
    time_window_hours = Column(Integer, default=24)  # Max time to complete funnel

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversionEvent(Base):
    """
    Tracks individual conversion events with attribution.
    """

    __tablename__ = "conversion_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    visitor_id = Column(String(255), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Conversion details
    conversion_type = Column(String(100), nullable=False, index=True)  # purchase, signup, etc.
    conversion_value = Column(Float)
    currency = Column(String(3), default="USD")

    # Attribution (first-touch, last-touch, multi-touch)
    first_touch_source = Column(String(255))
    first_touch_medium = Column(String(255))
    first_touch_campaign = Column(String(255))
    last_touch_source = Column(String(255))
    last_touch_medium = Column(String(255))
    last_touch_campaign = Column(String(255))

    # Journey
    touchpoint_count = Column(Integer)  # Number of sessions before conversion
    time_to_conversion_hours = Column(Float)

    # Ecommerce specific
    order_id = Column(String(255), index=True)
    product_ids = Column(JSONB)  # List of purchased products

    # Metadata
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_conversions_timestamp_type", "timestamp", "conversion_type"),
    )


class SessionReplay(Base):
    """
    Session replay metadata (actual replay data in S3/object storage).
    """

    __tablename__ = "session_replays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    visitor_id = Column(String(255), nullable=False, index=True)

    # Replay metadata
    duration_ms = Column(Integer)
    event_count = Column(Integer)  # Number of rrweb events
    storage_path = Column(String(1024))  # S3 path
    compressed_size_bytes = Column(Integer)

    # Recording config
    has_console_logs = Column(Boolean, default=False)
    has_network_data = Column(Boolean, default=False)
    privacy_mode = Column(String(50), default="strict")  # strict, balanced, off

    # Analysis
    has_errors = Column(Boolean, default=False)
    has_rage_clicks = Column(Boolean, default=False)
    quality_score = Column(Float)  # ML score for interesting sessions

    # Status
    processing_status = Column(String(50), default="pending")  # pending, processed, failed

    # Metadata
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Auto-delete for privacy
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_replays_recorded_at", "recorded_at"),
        Index("idx_replays_quality", "quality_score", postgresql_where=Column("quality_score") > 70),
    )


class HeatmapData(Base):
    """
    Aggregated heatmap data for pages.
    """

    __tablename__ = "heatmap_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_path = Column(String(1024), nullable=False, index=True)
    viewport_width = Column(Integer, nullable=False)  # Responsive buckets: 375, 768, 1024, 1920

    # Heatmap types
    click_map = Column(JSONB)  # {x: int, y: int, count: int}[]
    scroll_map = Column(JSONB)  # {depth_percent: int, reach_count: int}[]
    move_map = Column(JSONB)  # Mouse movement density
    attention_map = Column(JSONB)  # Time spent looking at areas

    # Aggregation metadata
    sample_size = Column(Integer)  # Number of sessions aggregated
    date_from = Column(DateTime, nullable=False)
    date_to = Column(DateTime, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_heatmap_page_viewport", "page_path", "viewport_width"),
    )
