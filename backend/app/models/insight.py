"""
Insight model - AI-generated business insights.
"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.shop import Shop


class InsightType(str, Enum):
    """Types of insights the system can generate."""

    TRAFFIC_SALES_MISMATCH = "traffic_sales_mismatch"
    UNDERSTOCKED_WINNER = "understocked_winner"
    OVERSTOCK_SLOW_MOVER = "overstock_slow_mover"
    COUPON_CANNIBALIZATION = "coupon_cannibalization"
    CHECKOUT_DROPOFF = "checkout_dropoff"
    PRICING_OPPORTUNITY = "pricing_opportunity"
    INVENTORY_ALERT = "inventory_alert"
    TREND_DETECTION = "trend_detection"


class InsightSeverity(str, Enum):
    """Severity levels for insights."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Insight(Base):
    """AI-generated insight with actionable recommendations."""

    __tablename__ = "insights"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        index=True,
    )

    # Insight classification
    type: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        default=InsightSeverity.MEDIUM.value,
    )

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    action_summary: Mapped[str] = mapped_column(Text, nullable=False)
    expected_uplift: Mapped[Optional[str]] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float, default=0.8)

    # Detailed payload (product IDs, metrics, etc.)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
    )

    # Deep link to Shopify admin
    admin_deep_link: Mapped[Optional[str]] = mapped_column(Text)

    # Lifecycle
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
    )
    actioned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
    )

    # Relationships
    shop: Mapped["Shop"] = relationship("Shop", back_populates="insights")

    @property
    def is_active(self) -> bool:
        """Check if insight is still active (not dismissed or expired)."""
        if self.dismissed_at:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True

    def __repr__(self) -> str:
        return f"<Insight {self.type}: {self.title[:30]}>"
