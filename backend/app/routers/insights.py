"""
Insights API routes.
"""
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


async def get_insight_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InsightRepository:
    """Dependency to get insight repository."""
    return InsightRepository(session)


@router.get("", response_model=PaginatedInsightsResponse)
async def list_insights(
    shop_id: Annotated[UUID, Query(description="Shop ID to get insights for")],
    repo: Annotated[InsightRepository, Depends(get_insight_repository)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    insight_type: Optional[str] = Query(None, alias="type", description="Filter by type"),
) -> PaginatedInsightsResponse:
    """
    Get paginated list of active insights for a shop.

    Supports filtering by severity and type.
    Returns only non-dismissed insights by default.
    """
    # Validate severity if provided
    if severity and severity not in ["critical", "high", "medium", "low"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid severity. Must be: critical, high, medium, or low",
        )

    skip = (page - 1) * page_size
    insights, total = await repo.get_active_for_shop(
        shop_id=shop_id,
        severity=severity,
        insight_type=insight_type,
        skip=skip,
        limit=page_size,
    )

    items = [InsightResponse.model_validate(i) for i in insights]

    return PaginatedInsightsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(insights)) < total,
    )


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(
    insight_id: UUID,
    repo: Annotated[InsightRepository, Depends(get_insight_repository)],
) -> InsightResponse:
    """Get a single insight by ID."""
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
    repo: Annotated[InsightRepository, Depends(get_insight_repository)],
) -> InsightDismissResponse:
    """Mark an insight as dismissed."""
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
    repo: Annotated[InsightRepository, Depends(get_insight_repository)],
) -> dict:
    """Mark that user took action on an insight."""
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
    repo: Annotated[InsightRepository, Depends(get_insight_repository)],
) -> dict:
    """Get insight statistics for a shop."""
    return await repo.get_insight_stats(shop_id)
