"""
Pydantic schemas package.
"""
from app.schemas.dashboard import (
    DashboardStats,
    DashboardSummary,
    RevenueChartData,
    RevenueDataPoint,
    TopProduct,
    TopProductsResponse,
)
from app.schemas.insight import (
    InsightBase,
    InsightDismissResponse,
    InsightFilters,
    InsightResponse,
    PaginatedInsightsResponse,
)
from app.schemas.shop import (
    ShopBase,
    ShopCreate,
    ShopResponse,
    ShopSyncRequest,
    ShopSyncResponse,
    ShopUpdate,
)

__all__ = [
    # Shop
    "ShopBase",
    "ShopCreate",
    "ShopUpdate",
    "ShopResponse",
    "ShopSyncRequest",
    "ShopSyncResponse",
    # Insight
    "InsightBase",
    "InsightResponse",
    "InsightDismissResponse",
    "InsightFilters",
    "PaginatedInsightsResponse",
    # Dashboard
    "DashboardStats",
    "DashboardSummary",
    "RevenueChartData",
    "RevenueDataPoint",
    "TopProduct",
    "TopProductsResponse",
]
