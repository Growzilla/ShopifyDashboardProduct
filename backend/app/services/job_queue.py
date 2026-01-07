"""
ARQ Job Queue Service - Async Redis-based job queue for background tasks.

Provides:
- Code analysis job scheduling
- Notification delivery jobs
- Periodic batch processing
- Adaptive scheduling logic
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.code_analysis import (
    AnalysisResult,
    CodeSubmission,
    NotificationPreference,
    SubmissionStatus,
    TrafficMetric,
)
from app.services.ai_analyzer import ai_analyzer
from app.services.notification_service import notification_service

logger = get_logger(__name__)


def get_redis_settings() -> RedisSettings:
    """Get Redis connection settings from config."""
    redis_url = str(settings.redis_url) if settings.redis_url else "redis://localhost:6379"

    # Parse Redis URL
    if redis_url.startswith("redis://"):
        redis_url = redis_url[8:]

    parts = redis_url.split("@")
    if len(parts) == 2:
        auth, host_port = parts
        password = auth.split(":")[1] if ":" in auth else None
    else:
        host_port = parts[0]
        password = None

    host_db = host_port.split("/")
    host_port_part = host_db[0]
    database = int(host_db[1]) if len(host_db) > 1 else 0

    host, port = host_port_part.split(":") if ":" in host_port_part else (host_port_part, 6379)

    return RedisSettings(
        host=host,
        port=int(port),
        password=password,
        database=database,
    )


# ============================================
# JOB FUNCTIONS
# ============================================

async def analyze_code_job(
    ctx: dict,
    submission_id: str,
) -> dict[str, Any]:
    """
    Background job to analyze a code submission.

    Args:
        ctx: ARQ context with Redis connection
        submission_id: UUID of the code submission

    Returns:
        Analysis result summary
    """
    logger.info("Starting code analysis job", submission_id=submission_id)

    async with get_db_context() as session:
        # Get submission
        submission = await session.get(CodeSubmission, UUID(submission_id))
        if not submission:
            logger.error("Submission not found", submission_id=submission_id)
            return {"error": "Submission not found"}

        # Update status
        submission.status = SubmissionStatus.ANALYZING.value
        await session.commit()

        try:
            # Run AI analysis
            result = await ai_analyzer.analyze_code(
                code=submission.code,
                language=submission.language or "python",
            )

            # Calculate overall grade from scores
            scores = result.get("scores", {})
            avg_score = (
                scores.get("performance", 0) +
                scores.get("security", 0) +
                scores.get("quality", 0)
            ) / 3

            # Create analysis result record
            analysis_result = AnalysisResult(
                submission_id=submission.id,
                bugs=result.get("bugs", []),
                security_issues=result.get("security_issues", []),
                optimizations=result.get("optimizations", []),
                performance_suggestions=result.get("performance_suggestions", []),
                performance_score=scores.get("performance", 0),
                security_score=scores.get("security", 0),
                quality_score=scores.get("quality", 0),
                overall_grade=result.get("overall_grade", "C"),
                summary=result.get("summary", ""),
                ai_model=result.get("_metadata", {}).get("ai_model", "gpt-4"),
                tokens_used=result.get("_metadata", {}).get("tokens_used", 0),
                analysis_duration_ms=result.get("_metadata", {}).get("analysis_duration_ms", 0),
            )
            session.add(analysis_result)

            # Update submission status
            submission.status = SubmissionStatus.COMPLETED.value
            submission.analyzed_at = datetime.now(timezone.utc)

            await session.commit()

            # Queue notification job
            redis: ArqRedis = ctx["redis"]
            await redis.enqueue_job(
                "send_notification_job",
                submission_id,
            )

            logger.info(
                "Code analysis completed",
                submission_id=submission_id,
                grade=result.get("overall_grade"),
                tokens=result.get("_metadata", {}).get("tokens_used", 0),
            )

            return {
                "success": True,
                "grade": result.get("overall_grade"),
                "summary": result.get("summary"),
            }

        except Exception as e:
            logger.error(
                "Code analysis failed",
                submission_id=submission_id,
                error=str(e),
            )

            submission.status = SubmissionStatus.FAILED.value
            submission.error_message = str(e)
            submission.retry_count += 1
            await session.commit()

            # Retry if under limit
            if submission.retry_count < 3:
                redis: ArqRedis = ctx["redis"]
                await redis.enqueue_job(
                    "analyze_code_job",
                    submission_id,
                    _defer_by=timedelta(minutes=5 * submission.retry_count),
                )

            return {"error": str(e)}


async def send_notification_job(
    ctx: dict,
    submission_id: str,
) -> dict[str, Any]:
    """
    Background job to send notifications for completed analysis.
    """
    logger.info("Sending notifications", submission_id=submission_id)

    async with get_db_context() as session:
        # Get submission with result
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(CodeSubmission)
            .options(selectinload(CodeSubmission.analysis_result))
            .where(CodeSubmission.id == UUID(submission_id))
        )
        result = await session.execute(stmt)
        submission = result.scalar_one_or_none()

        if not submission or not submission.analysis_result:
            return {"error": "Submission or result not found"}

        # Get notification preferences
        prefs = await session.execute(
            select(NotificationPreference)
            .where(NotificationPreference.shop_id == submission.shop_id)
        )
        preferences = prefs.scalar_one_or_none()

        if not preferences:
            logger.info("No notification preferences found", shop_id=str(submission.shop_id))
            return {"skipped": True}

        analysis = submission.analysis_result
        notifications_sent = []

        # Send email
        if preferences.email_enabled and preferences.email_address:
            html, text = notification_service.format_analysis_email(
                submission_id=str(submission.id),
                grade=analysis.overall_grade,
                summary=analysis.summary or "",
                bugs_count=len(analysis.bugs),
                security_count=len(analysis.security_issues),
                optimizations_count=len(analysis.optimizations),
            )

            success = await notification_service.send_email(
                to=preferences.email_address,
                subject=f"Code Analysis Complete - Grade: {analysis.overall_grade}",
                html_content=html,
                text_content=text,
            )
            if success:
                notifications_sent.append("email")

        # Send webhook
        if preferences.webhook_enabled and preferences.webhook_url:
            payload = notification_service.format_webhook_payload(
                event_type="analysis.completed",
                submission_id=str(submission.id),
                result={
                    "overall_grade": analysis.overall_grade,
                    "summary": analysis.summary,
                    "scores": {
                        "performance": analysis.performance_score,
                        "security": analysis.security_score,
                        "quality": analysis.quality_score,
                    },
                    "bugs": analysis.bugs,
                    "security_issues": analysis.security_issues,
                    "optimizations": analysis.optimizations,
                },
            )

            success = await notification_service.send_webhook(
                url=preferences.webhook_url,
                payload=payload,
                secret=preferences.webhook_secret,
            )
            if success:
                notifications_sent.append("webhook")

        logger.info(
            "Notifications sent",
            submission_id=submission_id,
            channels=notifications_sent,
        )

        return {"sent": notifications_sent}


async def batch_analysis_job(ctx: dict) -> dict[str, Any]:
    """
    Periodic batch job to process pending submissions.
    Runs every 6 hours by default, or triggered by adaptive scheduler.
    """
    logger.info("Starting batch analysis job")

    async with get_db_context() as session:
        from sqlalchemy import select

        # Get pending submissions
        stmt = (
            select(CodeSubmission)
            .where(CodeSubmission.status == SubmissionStatus.PENDING.value)
            .order_by(CodeSubmission.created_at)
            .limit(100)  # Process in batches
        )
        result = await session.execute(stmt)
        submissions = result.scalars().all()

        if not submissions:
            logger.info("No pending submissions for batch processing")
            return {"processed": 0}

        # Queue each submission for analysis
        redis: ArqRedis = ctx["redis"]
        queued = 0

        for submission in submissions:
            submission.status = SubmissionStatus.QUEUED.value
            submission.queued_at = datetime.now(timezone.utc)

            await redis.enqueue_job(
                "analyze_code_job",
                str(submission.id),
            )
            queued += 1

        await session.commit()

        logger.info("Batch analysis queued", count=queued)
        return {"processed": queued}


async def check_adaptive_trigger(ctx: dict) -> dict[str, Any]:
    """
    Check if adaptive scheduling should trigger early batch processing.

    Triggers:
    - Traffic > 1000 requests/hour
    - Pending submissions > 50
    - Queue depth monitoring
    """
    async with get_db_context() as session:
        from sqlalchemy import func, select

        # Check pending submissions
        pending_count = await session.scalar(
            select(func.count())
            .select_from(CodeSubmission)
            .where(CodeSubmission.status == SubmissionStatus.PENDING.value)
        )

        # Check recent traffic
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_traffic = await session.scalar(
            select(func.sum(TrafficMetric.request_count))
            .where(TrafficMetric.hour >= hour_ago)
        ) or 0

        should_trigger = False
        reason = None

        if pending_count and pending_count > 50:
            should_trigger = True
            reason = f"pending_submissions: {pending_count}"
        elif recent_traffic > 1000:
            should_trigger = True
            reason = f"high_traffic: {recent_traffic}/hour"

        if should_trigger:
            logger.info(
                "Adaptive trigger activated",
                reason=reason,
                pending=pending_count,
                traffic=recent_traffic,
            )

            redis: ArqRedis = ctx["redis"]
            await redis.enqueue_job("batch_analysis_job")

            return {"triggered": True, "reason": reason}

        return {"triggered": False}


# ============================================
# WORKER SETTINGS
# ============================================

class WorkerSettings:
    """ARQ worker configuration."""

    functions = [
        analyze_code_job,
        send_notification_job,
        batch_analysis_job,
        check_adaptive_trigger,
    ]

    # Cron jobs
    cron_jobs = [
        # Batch analysis every 6 hours
        {
            "coroutine": batch_analysis_job,
            "hour": {0, 6, 12, 18},
            "minute": 0,
        },
        # Adaptive trigger check every 15 minutes
        {
            "coroutine": check_adaptive_trigger,
            "minute": {0, 15, 30, 45},
        },
    ]

    redis_settings = get_redis_settings()

    # Worker settings
    max_jobs = 10
    job_timeout = 600  # 10 minutes
    keep_result = 3600  # 1 hour
    retry_jobs = True
    max_tries = 3


async def create_queue_pool() -> ArqRedis:
    """Create ARQ Redis connection pool."""
    return await create_pool(get_redis_settings())
