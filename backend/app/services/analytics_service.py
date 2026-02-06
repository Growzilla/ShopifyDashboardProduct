"""
Analytics service - Helper functions for event processing and enrichment.

==============================================================================
MVP STATUS: DISABLED - This service is not imported/used in MVP.
The full analytics module is overengineered for initial launch.
To re-enable: uncomment analytics router in main.py
==============================================================================
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse
import hashlib
import re
from user_agents import parse as parse_ua
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
import structlog

from app.models.analytics import AnalyticsEvent, AnalyticsSession

logger = structlog.get_logger()

# Bot detection patterns
BOT_PATTERNS = [
    r"bot", r"crawler", r"spider", r"scraper", r"curl", r"wget",
    r"python-requests", r"axios", r"java", r"go-http-client",
    r"facebookexternalhit", r"twitterbot", r"linkedinbot",
]


def parse_user_agent(user_agent: str) -> Dict[str, Any]:
    """
    Parse User-Agent string to extract device, browser, and OS information.

    Args:
        user_agent: User-Agent header string

    Returns:
        Dictionary with device_type, browser, browser_version, os, os_version
    """
    try:
        ua = parse_ua(user_agent)

        # Determine device type
        if ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        elif ua.is_pc:
            device_type = "desktop"
        else:
            device_type = "unknown"

        return {
            "device_type": device_type,
            "browser": ua.browser.family,
            "browser_version": ua.browser.version_string,
            "os": ua.os.family,
            "os_version": ua.os.version_string,
            "is_mobile": ua.is_mobile,
            "is_tablet": ua.is_tablet,
            "is_bot": ua.is_bot,
        }
    except Exception as e:
        logger.error("user_agent_parse_failed", error=str(e), user_agent=user_agent)
        return {
            "device_type": "unknown",
            "browser": "Unknown",
            "browser_version": "",
            "os": "Unknown",
            "os_version": "",
            "is_mobile": False,
            "is_tablet": False,
            "is_bot": False,
        }


def detect_bot(user_agent: str, ua_data: Dict[str, Any]) -> bool:
    """
    Detect if the request is from a bot.

    Uses multiple signals:
    - User-Agent parsing
    - Pattern matching against known bot signatures
    - Behavioral analysis (future: ML-based)

    Args:
        user_agent: User-Agent header string
        ua_data: Parsed user agent data

    Returns:
        True if bot detected, False otherwise
    """
    # Check parsed UA
    if ua_data.get("is_bot"):
        return True

    # Pattern matching
    user_agent_lower = user_agent.lower()
    for pattern in BOT_PATTERNS:
        if re.search(pattern, user_agent_lower):
            return True

    # Empty or very short UA (likely bot)
    if not user_agent or len(user_agent) < 10:
        return True

    return False


def extract_referrer_domain(referrer: str) -> Optional[str]:
    """
    Extract domain from referrer URL.

    Args:
        referrer: Referrer URL

    Returns:
        Domain string or None
    """
    try:
        parsed = urlparse(referrer)
        domain = parsed.netloc

        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]

        return domain if domain else None
    except Exception:
        return None


def fingerprint_hash(data: str) -> str:
    """
    Create SHA-256 hash for fingerprinting.

    Args:
        data: String to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(data.encode()).hexdigest()


async def enrich_geo_data(event_id: str, ip_hash: Optional[str], db: AsyncSession) -> None:
    """
    Enrich event with geographic data based on IP address.

    NOTE: This is a placeholder. In production, integrate with:
    - MaxMind GeoIP2
    - IP2Location
    - ipapi.co
    - Or self-hosted GeoIP database

    Args:
        event_id: Event UUID
        ip_hash: Hashed IP address
        db: Database session
    """
    # TODO: Implement actual GeoIP lookup
    # For now, just log that enrichment would happen
    logger.debug("geo_enrichment_placeholder", event_id=event_id)

    # Example implementation with a GeoIP service:
    # try:
    #     geo_data = await geoip_lookup(ip_hash)
    #     await db.execute(
    #         update(AnalyticsEvent)
    #         .where(AnalyticsEvent.id == event_id)
    #         .values(
    #             country_code=geo_data.get("country_code"),
    #             country_name=geo_data.get("country_name"),
    #             region=geo_data.get("region"),
    #             city=geo_data.get("city"),
    #             timezone=geo_data.get("timezone"),
    #         )
    #     )
    #     await db.commit()
    # except Exception as e:
    #     logger.error("geo_enrichment_failed", error=str(e))

    pass


async def update_session_metrics(session_id: str, db: AsyncSession) -> None:
    """
    Update session-level aggregations when new events arrive.

    This function:
    1. Creates session if doesn't exist
    2. Updates session end time
    3. Increments event counters
    4. Calculates derived metrics (bounce rate, duration)

    Args:
        session_id: Session identifier
        db: Database session
    """
    try:
        # Get all events for this session
        events_query = (
            select(AnalyticsEvent)
            .where(AnalyticsEvent.session_id == session_id)
            .order_by(AnalyticsEvent.timestamp)
        )
        result = await db.execute(events_query)
        events = result.scalars().all()

        if not events:
            return

        first_event = events[0]
        last_event = events[-1]

        # Calculate metrics
        start_time = first_event.timestamp
        end_time = last_event.timestamp
        duration_seconds = int((end_time - start_time).total_seconds())

        pageview_count = sum(1 for e in events if e.event_type == "pageview")
        event_count = len(events)
        click_count = sum(1 for e in events if e.event_type == "click")

        # Bounce detection: single pageview and duration < 10 seconds
        is_bounce = pageview_count == 1 and duration_seconds < 10

        # Check for conversions
        has_conversion = any(e.ecommerce_data and e.event_type == "ecommerce" for e in events)
        conversion_value = sum(
            e.ecommerce_data.get("order_value", 0)
            for e in events
            if e.ecommerce_data and e.event_type == "ecommerce"
        )

        # Check existing session
        session_query = select(AnalyticsSession).where(
            AnalyticsSession.session_id == session_id
        )
        session_result = await db.execute(session_query)
        existing_session = session_result.scalar_one_or_none()

        if existing_session:
            # Update existing session
            existing_session.end_time = end_time
            existing_session.duration_seconds = duration_seconds
            existing_session.exit_page = last_event.path
            existing_session.pageview_count = pageview_count
            existing_session.event_count = event_count
            existing_session.click_count = click_count
            existing_session.is_bounce = is_bounce
            existing_session.has_conversion = has_conversion
            existing_session.conversion_value = conversion_value if has_conversion else None
            existing_session.updated_at = datetime.utcnow()
        else:
            # Create new session
            new_session = AnalyticsSession(
                session_id=session_id,
                visitor_id=first_event.visitor_id,
                user_id=first_event.user_id,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                entry_page=first_event.path,
                exit_page=last_event.path,
                pageview_count=pageview_count,
                event_count=event_count,
                click_count=click_count,
                initial_referrer=first_event.referrer,
                initial_utm_source=first_event.utm_source,
                initial_utm_medium=first_event.utm_medium,
                initial_utm_campaign=first_event.utm_campaign,
                device_type=first_event.device_type,
                browser=first_event.browser,
                os=first_event.os,
                country_code=first_event.country_code,
                is_bounce=is_bounce,
                has_conversion=has_conversion,
                conversion_value=conversion_value if has_conversion else None,
            )
            db.add(new_session)

        await db.commit()
        logger.debug("session_metrics_updated", session_id=session_id)

    except Exception as e:
        logger.error("session_update_failed", session_id=session_id, error=str(e))
        await db.rollback()


async def publish_to_event_stream(event: AnalyticsEvent) -> None:
    """
    Publish event to message broker (Kafka/Redpanda) for real-time processing.

    This enables:
    - Real-time dashboard updates via WebSocket
    - Stream processing for aggregations
    - Event replay for recovery
    - Integration with other systems

    Args:
        event: Analytics event to publish

    TODO: Implement actual Kafka/Redpanda integration
    """
    try:
        # Placeholder for event streaming
        logger.debug(
            "event_stream_publish_placeholder",
            event_id=str(event.id),
            event_type=event.event_type,
        )

        # Example with Kafka:
        # await kafka_producer.send(
        #     topic="analytics.events",
        #     value={
        #         "event_id": str(event.id),
        #         "event_type": event.event_type,
        #         "session_id": event.session_id,
        #         "visitor_id": event.visitor_id,
        #         "timestamp": event.timestamp.isoformat(),
        #         "url": event.url,
        #         "path": event.path,
        #         "properties": event.properties,
        #     }
        # )

    except Exception as e:
        logger.error("event_stream_publish_failed", error=str(e))


def calculate_funnel_conversion(steps: list, events: list) -> Dict[str, Any]:
    """
    Calculate conversion rates for a multi-step funnel.

    Args:
        steps: List of funnel step definitions
        events: List of analytics events

    Returns:
        Dictionary with step-by-step conversion metrics
    """
    # TODO: Implement funnel analysis
    # This will match URL patterns and calculate drop-off rates
    pass


def aggregate_heatmap_data(events: list, viewport_width: int) -> Dict[str, Any]:
    """
    Aggregate raw click/scroll events into heatmap data.

    Args:
        events: List of analytics events with interaction data
        viewport_width: Viewport width bucket

    Returns:
        Aggregated heatmap data structure
    """
    # TODO: Implement heatmap aggregation
    # This will cluster click coordinates and generate density maps
    pass


def calculate_session_quality_score(session: AnalyticsSession) -> float:
    """
    Calculate ML-based quality score for a session.

    Signals:
    - Duration
    - Engagement (clicks, scrolls)
    - Pages visited
    - Has conversion
    - Bounce vs engaged

    Returns:
        Score from 0-100 (higher = more likely to convert)

    TODO: Implement ML model for quality scoring
    """
    score = 50.0  # Base score

    # Duration bonus (up to 20 points)
    if session.duration_seconds > 300:  # 5+ minutes
        score += 20
    elif session.duration_seconds > 120:  # 2+ minutes
        score += 10
    elif session.duration_seconds > 30:  # 30+ seconds
        score += 5

    # Pageview bonus (up to 15 points)
    if session.pageview_count >= 5:
        score += 15
    elif session.pageview_count >= 3:
        score += 10
    elif session.pageview_count >= 2:
        score += 5

    # Engagement bonus (up to 15 points)
    if session.click_count >= 10:
        score += 15
    elif session.click_count >= 5:
        score += 10
    elif session.click_count >= 2:
        score += 5

    # Conversion (massive bonus)
    if session.has_conversion:
        score = 100.0

    # Bounce penalty
    if session.is_bounce:
        score = max(0, score - 30)

    return min(100.0, score)
