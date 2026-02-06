"""
Insights API routes.

MVP Analytics Dashboard - provides ONE AI-generated insight per store.
Includes demo insight fallback for development and testing.
"""
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.repositories.insight import InsightRepository
from app.schemas.insight import (
    InsightDismissResponse,
    InsightResponse,
    PaginatedInsightsResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])

# Demo shop UUID
DEMO_SHOP_UUID = UUID("00000000-0000-0000-0000-000000000001")


def _get_demo_insight() -> InsightResponse:
    """
    Return a single demo AI insight for testing.

    This is the ONE insight per store requirement for MVP.
    Clear, actionable, obviously valuable.
    """
    return InsightResponse(
        id=UUID("00000000-0000-0000-0000-000000000099"),
        shop_id=DEMO_SHOP_UUID,
        type="conversion_opportunity",
        severity="high",
        title="Mobile conversion rate is 40% lower than desktop",
        action_summary=(
            "Your mobile visitors convert at 1.2% vs 2.0% on desktop. "
            "Consider improving mobile checkout flow, reducing form fields, "
            "or adding mobile-specific payment options like Apple Pay."
        ),
        expected_uplift="+$850/month potential revenue",
        confidence=0.87,
        payload={
            "mobile_conversion_rate": 0.012,
            "desktop_conversion_rate": 0.020,
            "mobile_sessions": 4520,
            "desktop_sessions": 2180,
        },
        admin_deep_link="/settings/checkout",
        created_at=datetime.now(timezone.utc),
        dismissed_at=None,
    )


async def get_insight_repository(
    session: Annotated[AsyncSession | None, Depends(get_db_session)],
) -> InsightRepository | None:
    """
    Dependency to get insight repository.

    Returns None if database is not available (demo mode).
    """
    if session is None:
        return None
    return InsightRepository(session)


@router.get("", response_model=PaginatedInsightsResponse)
async def list_insights(
    shop_id: Annotated[UUID, Query(description="Shop ID to get insights for")],
    repo: Annotated[InsightRepository | None, Depends(get_insight_repository)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    insight_type: Optional[str] = Query(None, alias="type", description="Filter by type"),
) -> PaginatedInsightsResponse:
    """
    Get paginated list of active insights for a shop.

    Supports filtering by severity and type.
    Returns demo insight if no real insights exist or database unavailable (for MVP).
    """
    # Return demo insight if no database connection
    if repo is None:
        logger.info("No database connection, returning demo insight", shop_id=str(shop_id))
        demo = _get_demo_insight()
        demo.shop_id = shop_id
        return PaginatedInsightsResponse(
            items=[demo],
            total=1,
            page=1,
            page_size=page_size,
            has_more=False,
        )

    # Validate severity if provided
    if severity and severity not in ["critical", "high", "medium", "low"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid severity. Must be: critical, high, medium, or low",
        )

    skip = (page - 1) * page_size

    try:
        insights, total = await repo.get_active_for_shop(
            shop_id=shop_id,
            severity=severity,
            insight_type=insight_type,
            skip=skip,
            limit=page_size,
        )

        # If no insights found, return demo insight for MVP
        if total == 0 and page == 1:
            logger.info("No insights found, returning demo insight", shop_id=str(shop_id))
            demo = _get_demo_insight()
            # Update shop_id to match request
            demo.shop_id = shop_id
            return PaginatedInsightsResponse(
                items=[demo],
                total=1,
                page=1,
                page_size=page_size,
                has_more=False,
            )

        items = [InsightResponse.model_validate(i) for i in insights]

        return PaginatedInsightsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(skip + len(insights)) < total,
        )
    except Exception as e:
        logger.error("Failed to fetch insights", error=str(e), shop_id=str(shop_id))
        # Return demo insight on error to keep MVP working
        demo = _get_demo_insight()
        demo.shop_id = shop_id
        return PaginatedInsightsResponse(
            items=[demo],
            total=1,
            page=1,
            page_size=page_size,
            has_more=False,
        )


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(
    insight_id: UUID,
    repo: Annotated[InsightRepository | None, Depends(get_insight_repository)],
) -> InsightResponse:
    """Get a single insight by ID."""
    # Handle demo insight ID or demo mode
    if insight_id == UUID("00000000-0000-0000-0000-000000000099") or repo is None:
        return _get_demo_insight()

    insight = await repo.get_by_id(insight_id)
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )
    return InsightResponse.model_validate(insight)


@router.post("/{insight_id}/dismiss", response_model=InsightDismissResponse)
async def dismiss_insight(
    insight_id: UUID,
    repo: Annotated[InsightRepository | None, Depends(get_insight_repository)],
) -> InsightDismissResponse:
    """Mark an insight as dismissed."""
    # Handle demo insight dismissal or demo mode gracefully
    if insight_id == UUID("00000000-0000-0000-0000-000000000099") or repo is None:
        return InsightDismissResponse(
            id=insight_id,
            dismissed_at=datetime.now(timezone.utc),
            message="Demo insight dismissed",
        )

    insight = await repo.get_by_id(insight_id)
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )

    if insight.dismissed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insight already dismissed",
        )

    insight = await repo.dismiss(insight)
    logger.info("Dismissed insight", insight_id=str(insight_id))

    return InsightDismissResponse(
        id=insight.id,
        dismissed_at=insight.dismissed_at,  # type: ignore
    )


@router.post("/{insight_id}/action")
async def mark_insight_actioned(
    insight_id: UUID,
    repo: Annotated[InsightRepository | None, Depends(get_insight_repository)],
) -> dict:
    """Mark that user took action on an insight."""
    # Handle demo insight action or demo mode gracefully
    if insight_id == UUID("00000000-0000-0000-0000-000000000099") or repo is None:
        return {"message": "Demo insight marked as actioned", "id": str(insight_id)}

    insight = await repo.get_by_id(insight_id)
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )

    await repo.mark_actioned(insight)
    logger.info("Insight actioned", insight_id=str(insight_id))

    return {"message": "Insight marked as actioned", "id": str(insight_id)}


@router.get("/stats/{shop_id}")
async def get_insight_stats(
    shop_id: UUID,
    repo: Annotated[InsightRepository | None, Depends(get_insight_repository)],
) -> dict:
    """Get insight statistics for a shop."""
    # Return demo stats if no database connection
    demo_stats = {
        "total": 1,
        "active": 1,
        "dismissed": 0,
        "actioned": 0,
        "by_severity": {"high": 1},
        "by_type": {"conversion_opportunity": 1},
    }

    if repo is None:
        return demo_stats

    try:
        stats = await repo.get_insight_stats(shop_id)
        # If no stats, return demo stats
        if stats.get("total", 0) == 0:
            return demo_stats
        return stats
    except Exception:
        # Return demo stats on error
        return {
            "total": 1,
            "active": 1,
            "dismissed": 0,
            "actioned": 0,
            "by_severity": {"high": 1},
            "by_type": {"conversion_opportunity": 1},
        }
