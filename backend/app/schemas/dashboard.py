"""
Dashboard Pydantic schemas for analytics data.
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DashboardStats(BaseModel):
    """Dashboard statistics summary."""

    yesterday_revenue: float = Field(alias="yesterdayRevenue")
    week_avg_revenue: float = Field(alias="weekAvgRevenue")
    yesterday_orders: int = Field(alias="yesterdayOrders")
    week_avg_orders: int = Field(alias="weekAvgOrders")
    yesterday_aov: float = Field(alias="yesterdayAov")
    week_avg_aov: float = Field(alias="weekAvgAov")
    revenue_delta: float = Field(alias="revenueDelta")
    orders_delta: float = Field(alias="ordersDelta")
    aov_delta: float = Field(alias="aovDelta")

    model_config = ConfigDict(populate_by_name=True)


class RevenueDataPoint(BaseModel):
    """Single data point for revenue chart."""

    date: date
    revenue: float
    orders: int
    aov: float


class RevenueChartData(BaseModel):
    """Revenue chart data over time."""

    data: list[RevenueDataPoint]
    period: str
    total_revenue: float = Field(alias="totalRevenue")
    total_orders: int = Field(alias="totalOrders")

    model_config = ConfigDict(populate_by_name=True)


class TopProduct(BaseModel):
    """Top performing product."""

    id: str
    title: str
    revenue: float
    units_sold: int = Field(alias="unitsSold")
    image_url: Optional[str] = Field(None, alias="imageUrl")

    model_config = ConfigDict(populate_by_name=True)


class TopProductsResponse(BaseModel):
    """Response for top products endpoint."""

    products: list[TopProduct]
    period: str


class DashboardSummary(BaseModel):
    """Complete dashboard summary."""

    stats: DashboardStats
    revenue_chart: RevenueChartData = Field(alias="revenueChart")
    top_products: list[TopProduct] = Field(alias="topProducts")
    active_insights_count: int = Field(alias="activeInsightsCount")

    model_config = ConfigDict(populate_by_name=True)
