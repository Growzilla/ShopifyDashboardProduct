"""
Dashboard API routes for analytics data.
"""
from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.models.insight import Insight
from app.models.order import Order
from app.models.shop import Shop
from app.schemas.dashboard import (
    DashboardStats,
    DashboardSummary,
    RevenueChartData,
    RevenueDataPoint,
    TopProduct,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    shop_id: Annotated[UUID, Query(description="Shop ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardStats:
    """
    Get dashboard statistics comparing yesterday to weekly average.
    """
    # Verify shop exists
    shop = await session.get(Shop, shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found",
        )

    today = date.today()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=7)

    # Get yesterday's metrics
    yesterday_stmt = select(
        func.sum(Order.total_price).label("revenue"),
        func.count(Order.id).label("orders"),
    ).where(
        Order.shop_id == shop_id,
        func.date(Order.processed_at) == yesterday,
    )
    yesterday_result = await session.execute(yesterday_stmt)
    yesterday_row = yesterday_result.one()
    yesterday_revenue = float(yesterday_row.revenue or 0)
    yesterday_orders = int(yesterday_row.orders or 0)
    yesterday_aov = yesterday_revenue / yesterday_orders if yesterday_orders > 0 else 0

    # Get week average metrics
    week_stmt = select(
        func.sum(Order.total_price).label("revenue"),
        func.count(Order.id).label("orders"),
    ).where(
        Order.shop_id == shop_id,
        func.date(Order.processed_at) >= week_start,
        func.date(Order.processed_at) < today,
    )
    week_result = await session.execute(week_stmt)
    week_row = week_result.one()
    week_revenue = float(week_row.revenue or 0)
    week_orders = int(week_row.orders or 0)

    # Calculate averages (7 days)
    week_avg_revenue = week_revenue / 7
    week_avg_orders = week_orders / 7
    week_avg_aov = week_revenue / week_orders if week_orders > 0 else 0

    # Calculate deltas (percentage change)
    revenue_delta = (
        ((yesterday_revenue - week_avg_revenue) / week_avg_revenue * 100)
        if week_avg_revenue > 0
        else 0
    )
    orders_delta = (
        ((yesterday_orders - week_avg_orders) / week_avg_orders * 100)
        if week_avg_orders > 0
        else 0
    )
    aov_delta = (
        ((yesterday_aov - week_avg_aov) / week_avg_aov * 100)
        if week_avg_aov > 0
        else 0
    )

    return DashboardStats(
        yesterday_revenue=round(yesterday_revenue, 2),
        week_avg_revenue=round(week_avg_revenue, 2),
        yesterday_orders=yesterday_orders,
        week_avg_orders=int(week_avg_orders),
        yesterday_aov=round(yesterday_aov, 2),
        week_avg_aov=round(week_avg_aov, 2),
        revenue_delta=round(revenue_delta, 1),
        orders_delta=round(orders_delta, 1),
        aov_delta=round(aov_delta, 1),
    )


@router.get("/revenue-chart", response_model=RevenueChartData)
async def get_revenue_chart(
    shop_id: Annotated[UUID, Query(description="Shop ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: str = Query("7d", description="Period: 7d, 30d, 90d"),
) -> RevenueChartData:
    """Get revenue chart data for the specified period."""
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 7)
    start_date = date.today() - timedelta(days=days)

    # Get daily aggregates
    stmt = (
        select(
            func.date(Order.processed_at).label("day"),
            func.sum(Order.total_price).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .where(
            Order.shop_id == shop_id,
            func.date(Order.processed_at) >= start_date,
        )
        .group_by(func.date(Order.processed_at))
        .order_by(func.date(Order.processed_at))
    )

    result = await session.execute(stmt)
    rows = result.all()

    data = [
        RevenueDataPoint(
            date=row.day,
            revenue=float(row.revenue or 0),
            orders=int(row.orders or 0),
            aov=float(row.revenue or 0) / int(row.orders or 1) if row.orders else 0,
        )
        for row in rows
    ]

    total_revenue = sum(d.revenue for d in data)
    total_orders = sum(d.orders for d in data)

    return RevenueChartData(
        data=data,
        period=period,
        total_revenue=round(total_revenue, 2),
        total_orders=total_orders,
    )


@router.get("/top-products")
async def get_top_products(
    shop_id: Annotated[UUID, Query(description="Shop ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(10, ge=1, le=50),
    period: str = Query("30d", description="Period: 7d, 30d, 90d"),
) -> dict:
    """Get top selling products for the period."""
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    start_date = date.today() - timedelta(days=days)

    # Get orders with line items
    stmt = select(Order).where(
        Order.shop_id == shop_id,
        func.date(Order.processed_at) >= start_date,
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()

    # Aggregate by product
    product_stats: dict[str, dict] = {}
    for order in orders:
        for item in order.line_items or []:
            product_id = item.get("product", {}).get("id")
            if not product_id:
                continue

            if product_id not in product_stats:
                product_stats[product_id] = {
                    "id": product_id,
                    "title": item.get("title", "Unknown"),
                    "revenue": 0,
                    "units_sold": 0,
                    "image_url": None,
                }

            revenue = float(
                item.get("originalTotalSet", {})
                .get("shopMoney", {})
                .get("amount", 0)
            )
            product_stats[product_id]["revenue"] += revenue
            product_stats[product_id]["units_sold"] += item.get("quantity", 0)

    # Sort by revenue and take top N
    sorted_products = sorted(
        product_stats.values(),
        key=lambda x: x["revenue"],
        reverse=True,
    )[:limit]

    products = [
        TopProduct(
            id=p["id"],
            title=p["title"],
            revenue=round(p["revenue"], 2),
            units_sold=p["units_sold"],
            image_url=p["image_url"],
        )
        for p in sorted_products
    ]

    return {"products": products, "period": period}


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    shop_id: Annotated[UUID, Query(description="Shop ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardSummary:
    """Get complete dashboard summary in a single call."""
    stats = await get_dashboard_stats(shop_id, session)
    revenue_chart = await get_revenue_chart(shop_id, session, "7d")
    top_products_response = await get_top_products(shop_id, session, 5, "30d")

    # Get active insights count
    insights_stmt = select(func.count()).select_from(Insight).where(
        Insight.shop_id == shop_id,
        Insight.dismissed_at.is_(None),
    )
    result = await session.execute(insights_stmt)
    active_insights_count = result.scalar() or 0

    return DashboardSummary(
        stats=stats,
        revenue_chart=revenue_chart,
        top_products=top_products_response["products"],
        active_insights_count=active_insights_count,
    )
