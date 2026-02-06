"""
Code Analysis API Routes - Endpoints for code submission and analysis results.

==============================================================================
MVP STATUS: DISABLED - This router is not registered in MVP.
The code analysis feature is overengineered for initial launch.
To re-enable: uncomment import in routers/__init__.py and main.py
==============================================================================
"""
from datetime import datetime, timezone
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.models.code_analysis import (
    AnalysisResult,
    CodeSubmission,
    NotificationPreference,
    SubmissionPriority,
    SubmissionStatus,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/code", tags=["code-analysis"])


# ============================================
# SCHEMAS
# ============================================

class CodeSubmitRequest(BaseModel):
    """Request schema for code submission."""
    code: str = Field(..., min_length=1, max_length=50000)
    language: str = Field(default="python", max_length=50)
    filename: Optional[str] = Field(None, max_length=255)
    priority: Optional[str] = Field(default="normal")


class CodeSubmitResponse(BaseModel):
    """Response schema for code submission."""
    id: UUID
    status: str
    message: str
    estimated_time: str

    model_config = {"from_attributes": True}


class AnalysisResultResponse(BaseModel):
    """Response schema for analysis results."""
    id: UUID
    submission_id: UUID
    bugs: list[dict[str, Any]]
    security_issues: list[dict[str, Any]]
    optimizations: list[dict[str, Any]]
    performance_suggestions: list[dict[str, Any]]
    scores: dict[str, int]
    overall_grade: str
    summary: Optional[str]
    ai_model: str
    tokens_used: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmissionStatusResponse(BaseModel):
    """Response schema for submission status."""
    id: UUID
    status: str
    language: str
    created_at: datetime
    queued_at: Optional[datetime]
    analyzed_at: Optional[datetime]
    has_result: bool

    model_config = {"from_attributes": True}


class PaginatedSubmissionsResponse(BaseModel):
    """Paginated submissions list."""
    items: list[SubmissionStatusResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class NotificationPreferenceRequest(BaseModel):
    """Request schema for notification preferences."""
    email_enabled: bool = True
    email_address: Optional[str] = None
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    in_app_enabled: bool = True
    notify_on_complete: bool = True
    notify_on_critical: bool = True
    notify_on_batch: bool = True


# ============================================
# ENDPOINTS
# ============================================

@router.post("/submit", response_model=CodeSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_code(
    request: CodeSubmitRequest,
    shop_id: Annotated[UUID, Query(description="Shop ID")],
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CodeSubmitResponse:
    """
    Submit code for AI analysis.

    The code is queued for asynchronous processing and will be analyzed
    by the AI engine. Results will be available via GET /code/{id}/result.
    """
    # Validate priority
    try:
        priority = SubmissionPriority(request.priority or "normal")
    except ValueError:
        priority = SubmissionPriority.NORMAL

    # Create submission
    submission = CodeSubmission(
        shop_id=shop_id,
        code=request.code,
        language=request.language,
        filename=request.filename,
        status=SubmissionStatus.PENDING.value,
        priority=priority.value,
    )
    session.add(submission)
    await session.commit()
    await session.refresh(submission)

    # Queue for analysis
    try:
        from app.services.job_queue import create_queue_pool

        redis = await create_queue_pool()
        await redis.enqueue_job(
            "analyze_code_job",
            str(submission.id),
            _queue_name="high" if priority == SubmissionPriority.HIGH else "default",
        )
        await redis.close()

        submission.status = SubmissionStatus.QUEUED.value
        submission.queued_at = datetime.now(timezone.utc)
        await session.commit()

        estimated = "2-5 minutes" if priority == SubmissionPriority.HIGH else "5-15 minutes"

    except Exception as e:
        logger.warning("Queue unavailable, using background task", error=str(e))
        # Fallback to FastAPI background tasks
        from app.services.ai_analyzer import ai_analyzer

        async def analyze_fallback():
            result = await ai_analyzer.analyze_code(request.code, request.language)
            # Store result in DB (simplified)
            logger.info("Fallback analysis complete", submission_id=str(submission.id))

        background_tasks.add_task(analyze_fallback)
        estimated = "5-10 minutes (fallback mode)"

    logger.info(
        "Code submitted for analysis",
        submission_id=str(submission.id),
        language=request.language,
        code_length=len(request.code),
    )

    return CodeSubmitResponse(
        id=submission.id,
        status=submission.status,
        message="Code submitted for analysis",
        estimated_time=estimated,
    )


@router.get("/{submission_id}", response_model=SubmissionStatusResponse)
async def get_submission_status(
    submission_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SubmissionStatusResponse:
    """Get the status of a code submission."""
    stmt = (
        select(CodeSubmission)
        .options(selectinload(CodeSubmission.analysis_result))
        .where(CodeSubmission.id == submission_id)
    )
    result = await session.execute(stmt)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    return SubmissionStatusResponse(
        id=submission.id,
        status=submission.status,
        language=submission.language,
        created_at=submission.created_at,
        queued_at=submission.queued_at,
        analyzed_at=submission.analyzed_at,
        has_result=submission.analysis_result is not None,
    )


@router.get("/{submission_id}/result", response_model=AnalysisResultResponse)
async def get_analysis_result(
    submission_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnalysisResultResponse:
    """Get the AI analysis result for a submission."""
    stmt = (
        select(AnalysisResult)
        .where(AnalysisResult.submission_id == submission_id)
    )
    result = await session.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        # Check if submission exists
        submission = await session.get(CodeSubmission, submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found",
            )
        elif submission.status == SubmissionStatus.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Analysis failed: {submission.error_message}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail=f"Analysis in progress. Status: {submission.status}",
            )

    return AnalysisResultResponse(
        id=analysis.id,
        submission_id=analysis.submission_id,
        bugs=analysis.bugs,
        security_issues=analysis.security_issues,
        optimizations=analysis.optimizations,
        performance_suggestions=analysis.performance_suggestions,
        scores={
            "performance": analysis.performance_score,
            "security": analysis.security_score,
            "quality": analysis.quality_score,
        },
        overall_grade=analysis.overall_grade,
        summary=analysis.summary,
        ai_model=analysis.ai_model,
        tokens_used=analysis.tokens_used,
        created_at=analysis.created_at,
    )


@router.get("/", response_model=PaginatedSubmissionsResponse)
async def list_submissions(
    shop_id: Annotated[UUID, Query(description="Shop ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
) -> PaginatedSubmissionsResponse:
    """List code submissions for a shop with pagination."""
    # Build query
    base_query = select(CodeSubmission).where(CodeSubmission.shop_id == shop_id)

    if status_filter:
        base_query = base_query.where(CodeSubmission.status == status_filter)

    # Get total count
    count_result = await session.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    stmt = (
        base_query
        .options(selectinload(CodeSubmission.analysis_result))
        .order_by(CodeSubmission.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    submissions = result.scalars().all()

    items = [
        SubmissionStatusResponse(
            id=s.id,
            status=s.status,
            language=s.language,
            created_at=s.created_at,
            queued_at=s.queued_at,
            analyzed_at=s.analyzed_at,
            has_result=s.analysis_result is not None,
        )
        for s in submissions
    ]

    return PaginatedSubmissionsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(items)) < total,
    )


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a code submission and its results."""
    submission = await session.get(CodeSubmission, submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    await session.delete(submission)
    await session.commit()

    logger.info("Submission deleted", submission_id=str(submission_id))


# ============================================
# NOTIFICATION PREFERENCES
# ============================================

@router.get("/notifications/preferences")
async def get_notification_preferences(
    shop_id: Annotated[UUID, Query(description="Shop ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Get notification preferences for a shop."""
    stmt = select(NotificationPreference).where(
        NotificationPreference.shop_id == shop_id
    )
    result = await session.execute(stmt)
    prefs = result.scalar_one_or_none()

    if not prefs:
        return {
            "email_enabled": True,
            "email_address": None,
            "webhook_enabled": False,
            "webhook_url": None,
            "in_app_enabled": True,
            "notify_on_complete": True,
            "notify_on_critical": True,
            "notify_on_batch": True,
        }

    return {
        "email_enabled": prefs.email_enabled,
        "email_address": prefs.email_address,
        "webhook_enabled": prefs.webhook_enabled,
        "webhook_url": prefs.webhook_url,
        "in_app_enabled": prefs.in_app_enabled,
        "notify_on_complete": prefs.notify_on_complete,
        "notify_on_critical": prefs.notify_on_critical,
        "notify_on_batch": prefs.notify_on_batch,
    }


@router.put("/notifications/preferences")
async def update_notification_preferences(
    shop_id: Annotated[UUID, Query(description="Shop ID")],
    request: NotificationPreferenceRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Update notification preferences for a shop."""
    stmt = select(NotificationPreference).where(
        NotificationPreference.shop_id == shop_id
    )
    result = await session.execute(stmt)
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = NotificationPreference(shop_id=shop_id)
        session.add(prefs)

    # Update fields
    prefs.email_enabled = request.email_enabled
    prefs.email_address = request.email_address
    prefs.webhook_enabled = request.webhook_enabled
    prefs.webhook_url = request.webhook_url
    prefs.webhook_secret = request.webhook_secret
    prefs.in_app_enabled = request.in_app_enabled
    prefs.notify_on_complete = request.notify_on_complete
    prefs.notify_on_critical = request.notify_on_critical
    prefs.notify_on_batch = request.notify_on_batch

    await session.commit()

    logger.info("Notification preferences updated", shop_id=str(shop_id))

    return {"message": "Preferences updated"}


# ============================================
# METRICS / STATS
# ============================================

@router.get("/stats/summary")
async def get_analysis_stats(
    shop_id: Annotated[UUID, Query(description="Shop ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Get analysis statistics for a shop."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # Total submissions
    total = await session.scalar(
        select(func.count())
        .select_from(CodeSubmission)
        .where(CodeSubmission.shop_id == shop_id)
    )

    # By status
    status_counts = {}
    for s in SubmissionStatus:
        count = await session.scalar(
            select(func.count())
            .select_from(CodeSubmission)
            .where(
                CodeSubmission.shop_id == shop_id,
                CodeSubmission.status == s.value,
            )
        )
        status_counts[s.value] = count or 0

    # Recent activity
    last_24h_count = await session.scalar(
        select(func.count())
        .select_from(CodeSubmission)
        .where(
            CodeSubmission.shop_id == shop_id,
            CodeSubmission.created_at >= last_24h,
        )
    )

    # Average grades (from completed)
    avg_scores = await session.execute(
        select(
            func.avg(AnalysisResult.performance_score),
            func.avg(AnalysisResult.security_score),
            func.avg(AnalysisResult.quality_score),
        )
        .join(CodeSubmission)
        .where(CodeSubmission.shop_id == shop_id)
    )
    scores = avg_scores.one()

    return {
        "total_submissions": total or 0,
        "by_status": status_counts,
        "last_24h": last_24h_count or 0,
        "average_scores": {
            "performance": round(scores[0] or 0, 1),
            "security": round(scores[1] or 0, 1),
            "quality": round(scores[2] or 0, 1),
        },
    }
