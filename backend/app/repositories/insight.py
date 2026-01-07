"""
Insight repository for data access operations.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select

from app.models.insight import Insight
from app.repositories.base import BaseRepository


class InsightRepository(BaseRepository[Insight]):
    """Repository for Insight model operations."""

    model = Insight

    async def get_active_for_shop(
        self,
        shop_id: UUID,
        *,
        severity: Optional[str] = None,
        insight_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Insight], int]:
        """
        Get active (non-dismissed) insights for a shop with filtering.
        Returns (insights, total_count) tuple.
        """
        # Base query for active insights
        base_query = select(Insight).where(
            Insight.shop_id == shop_id,
            Insight.dismissed_at.is_(None),
        )

        # Apply filters
        if severity:
            base_query = base_query.where(Insight.severity == severity)
        if insight_type:
            base_query = base_query.where(Insight.type == insight_type)

        # Get total count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get paginated results
        stmt = (
            base_query
            .order_by(Insight.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        insights = list(result.scalars().all())

        return insights, total

    async def dismiss(self, insight: Insight) -> Insight:
        """Mark an insight as dismissed."""
        insight.dismissed_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(insight)
        return insight

    async def mark_actioned(self, insight: Insight) -> Insight:
        """Mark an insight as actioned (user took recommended action)."""
        insight.actioned_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(insight)
        return insight

    async def bulk_create(
        self,
        shop_id: UUID,
        insights_data: list[dict],
    ) -> list[Insight]:
        """Create multiple insights at once."""
        insights = [
            Insight(shop_id=shop_id, **data)
            for data in insights_data
        ]
        self.session.add_all(insights)
        await self.session.flush()
        return insights

    async def get_insight_stats(self, shop_id: UUID) -> dict:
        """Get insight statistics for a shop."""
        # Count by severity
        severity_stmt = (
            select(Insight.severity, func.count())
            .where(
                Insight.shop_id == shop_id,
                Insight.dismissed_at.is_(None),
            )
            .group_by(Insight.severity)
        )
        severity_result = await self.session.execute(severity_stmt)
        severity_counts = dict(severity_result.all())

        # Count by type
        type_stmt = (
            select(Insight.type, func.count())
            .where(
                Insight.shop_id == shop_id,
                Insight.dismissed_at.is_(None),
            )
            .group_by(Insight.type)
        )
        type_result = await self.session.execute(type_stmt)
        type_counts = dict(type_result.all())

        return {
            "by_severity": severity_counts,
            "by_type": type_counts,
            "total_active": sum(severity_counts.values()),
        }
