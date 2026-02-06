"""
Code Analysis Models - Database models for code submission and AI analysis.

==============================================================================
MVP STATUS: DISABLED - These models are not imported in MVP.
The code analysis feature is overengineered for initial launch.
Tables exist in DB but are not used. To re-enable: uncomment in models/__init__.py
==============================================================================
"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.shop import Shop


class SubmissionStatus(str, Enum):
    """Status of code submission."""
    PENDING = "pending"
    QUEUED = "queued"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubmissionPriority(str, Enum):
    """Priority levels for analysis."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class CodeSubmission(Base):
    """
    Code submission for AI analysis.
    Stores user-submitted code snippets pending or completed analysis.
    """
    __tablename__ = "code_submissions"

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

    # Code content
    code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(50), default="python")
    filename: Mapped[Optional[str]] = mapped_column(String(255))

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20),
        default=SubmissionStatus.PENDING.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(10),
        default=SubmissionPriority.NORMAL.value,
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    shop: Mapped["Shop"] = relationship("Shop", back_populates="code_submissions")
    analysis_result: Mapped[Optional["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CodeSubmission {self.id} [{self.status}]>"


class AnalysisResult(Base):
    """
    AI analysis results for a code submission.
    Contains bugs, security issues, optimizations, and scores.
    """
    __tablename__ = "analysis_results"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    submission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("code_submissions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Analysis findings
    bugs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
    )
    security_issues: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
    )
    optimizations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
    )
    performance_suggestions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
    )

    # Scores
    performance_score: Mapped[int] = mapped_column(Integer, default=0)
    security_score: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    overall_grade: Mapped[str] = mapped_column(String(2), default="C")

    # Summary
    summary: Mapped[Optional[str]] = mapped_column(Text)

    # AI metadata
    ai_model: Mapped[str] = mapped_column(String(50), default="gpt-4-turbo-preview")
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    analysis_duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    submission: Mapped["CodeSubmission"] = relationship(
        "CodeSubmission",
        back_populates="analysis_result",
    )

    def __repr__(self) -> str:
        return f"<AnalysisResult {self.id} grade={self.overall_grade}>"


class NotificationPreference(Base):
    """
    User notification preferences for analysis results.
    """
    __tablename__ = "notification_preferences"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Email settings
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_address: Mapped[Optional[str]] = mapped_column(String(255))

    # Webhook settings
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_url: Mapped[Optional[str]] = mapped_column(Text)
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(64))

    # In-app settings
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Notification triggers
    notify_on_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_critical: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_batch: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TrafficMetric(Base):
    """
    Traffic metrics for adaptive scheduling.
    Tracks hourly request counts to trigger early analysis runs.
    """
    __tablename__ = "traffic_metrics"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Time bucket (hourly)
    hour: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        unique=True,
    )

    # Counts
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    submission_count: Mapped[int] = mapped_column(Integer, default=0)
    analysis_count: Mapped[int] = mapped_column(Integer, default=0)

    # Performance
    avg_response_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
