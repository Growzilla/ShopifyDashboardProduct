"""
Insight Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InsightBase(BaseModel):
    """Base insight schema."""

    type: str
    severity: str
    title: str
    action_summary: str = Field(alias="actionSummary")


class InsightResponse(InsightBase):
    """Schema for insight API responses."""

    id: UUID
    shop_id: UUID = Field(alias="shopId")
    expected_uplift: Optional[str] = Field(None, alias="expectedUplift")
    confidence: float
    payload: dict[str, Any]
    admin_deep_link: Optional[str] = Field(None, alias="adminDeepLink")
    created_at: datetime = Field(alias="createdAt")
    dismissed_at: Optional[datetime] = Field(None, alias="dismissedAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class PaginatedInsightsResponse(BaseModel):
    """Schema for paginated insights list."""

    items: list[InsightResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    has_more: bool = Field(alias="hasMore")

    model_config = ConfigDict(populate_by_name=True)


class InsightDismissResponse(BaseModel):
    """Response for dismissing an insight."""

    id: UUID
    dismissed_at: datetime = Field(alias="dismissedAt")
    message: str = "Insight dismissed"

    model_config = ConfigDict(populate_by_name=True)


class InsightFilters(BaseModel):
    """Query filters for insights."""

    severity: Optional[str] = None
    type: Optional[str] = None
    include_dismissed: bool = Field(False, alias="includeDismissed")

    model_config = ConfigDict(populate_by_name=True)
