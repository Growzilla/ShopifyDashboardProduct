"""
Insight generator - analyzes synced order/product data and creates actionable insights.

Called after data_sync completes. Generates 1-3 simple insights per sync.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.insight import Insight
from app.models.order import Order
from app.models.product import Product

logger = get_logger(__name__)


async def generate_insights(session: AsyncSession, shop_id: UUID) -> int:
    """
    Analyze synced data and generate insights for a shop.

    Returns the number of insights created.
    """
    count = 0

    try:
        # Get order stats for the last 30 days
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        # Total orders and revenue in last 30 days
        stats_stmt = select(
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_price).label("total_revenue"),
        ).where(
            Order.shop_id == shop_id,
            Order.processed_at >= thirty_days_ago,
        )
        result = await session.execute(stats_stmt)
        stats = result.one()

        total_orders = int(stats.total_orders or 0)
        total_revenue = float(stats.total_revenue or 0)

        if total_orders == 0:
            logger.info("No orders to analyze for insights", shop_id=str(shop_id))
            return 0

        # --- Insight 1: AOV Trend ---
        aov_30d = total_revenue / total_orders if total_orders > 0 else 0

        # Get last 7 days for comparison
        recent_stmt = select(
            func.count(Order.id).label("orders"),
            func.sum(Order.total_price).label("revenue"),
        ).where(
            Order.shop_id == shop_id,
            Order.processed_at >= seven_days_ago,
        )
        recent_result = await session.execute(recent_stmt)
        recent = recent_result.one()
        recent_orders = int(recent.orders or 0)
        recent_revenue = float(recent.revenue or 0)
        aov_7d = recent_revenue / recent_orders if recent_orders > 0 else 0

        if aov_30d > 0 and recent_orders >= 3:
            aov_change = ((aov_7d - aov_30d) / aov_30d) * 100

            if abs(aov_change) >= 5:  # Only report significant changes
                if aov_change > 0:
                    title = f"Average order value is up {aov_change:.0f}% this week"
                    action = (
                        f"Your AOV increased from ${aov_30d:.2f} (30-day avg) to ${aov_7d:.2f} (last 7 days). "
                        "Consider promoting bundles or upsells to maintain this momentum."
                    )
                    severity = "low"
                else:
                    title = f"Average order value dropped {abs(aov_change):.0f}% this week"
                    action = (
                        f"Your AOV fell from ${aov_30d:.2f} (30-day avg) to ${aov_7d:.2f} (last 7 days). "
                        "Consider adding product bundles, free shipping thresholds, or cross-sell recommendations."
                    )
                    severity = "medium"

                count += await _upsert_insight(
                    session,
                    shop_id=shop_id,
                    insight_type="trend_detection",
                    severity=severity,
                    title=title,
                    action_summary=action,
                    expected_uplift=f"AOV target: ${aov_30d:.2f}",
                    confidence=0.85,
                    payload={"aov_30d": aov_30d, "aov_7d": aov_7d, "change_pct": round(aov_change, 1)},
                )

        # --- Insight 2: Top Product by Revenue ---
        top_product_stmt = (
            select(
                Order.line_items,
            )
            .where(
                Order.shop_id == shop_id,
                Order.processed_at >= thirty_days_ago,
            )
        )
        top_result = await session.execute(top_product_stmt)
        orders = top_result.scalars().all()

        product_revenue: dict[str, dict] = {}
        for line_items in orders:
            for item in (line_items or []):
                product_id = item.get("product_id") or (item.get("product", {}) or {}).get("id")
                if not product_id:
                    continue
                if product_id not in product_revenue:
                    product_revenue[product_id] = {
                        "title": item.get("title", "Unknown"),
                        "revenue": 0,
                        "quantity": 0,
                    }
                product_revenue[product_id]["revenue"] += float(item.get("amount", 0))
                product_revenue[product_id]["quantity"] += int(item.get("quantity", 0))

        if product_revenue:
            top = max(product_revenue.items(), key=lambda x: x[1]["revenue"])
            top_id, top_data = top
            revenue_share = (top_data["revenue"] / total_revenue * 100) if total_revenue > 0 else 0

            if revenue_share >= 20:  # Only report if product is significant
                count += await _upsert_insight(
                    session,
                    shop_id=shop_id,
                    insight_type="pricing_opportunity",
                    severity="medium",
                    title=f'"{top_data["title"]}" drives {revenue_share:.0f}% of your revenue',
                    action_summary=(
                        f'Your top product generated ${top_data["revenue"]:.2f} from {top_data["quantity"]} units. '
                        "Consider protecting this revenue by maintaining stock levels and testing a small price increase."
                    ),
                    expected_uplift=f"+${top_data['revenue'] * 0.05:.0f}/month with 5% price test",
                    confidence=0.90,
                    payload={
                        "product_id": top_id,
                        "product_title": top_data["title"],
                        "revenue": top_data["revenue"],
                        "units": top_data["quantity"],
                        "revenue_share_pct": round(revenue_share, 1),
                    },
                )

        # --- Insight 3: Low Inventory Alert ---
        low_stock_stmt = select(Product).where(
            Product.shop_id == shop_id,
            Product.inventory_tracked == True,
            Product.total_inventory <= 5,
            Product.total_inventory > 0,
            Product.status == "active",
        )
        low_stock_result = await session.execute(low_stock_stmt)
        low_stock_products = low_stock_result.scalars().all()

        if low_stock_products:
            product_names = [p.title for p in low_stock_products[:3]]
            names_str = ", ".join(product_names)
            if len(low_stock_products) > 3:
                names_str += f" and {len(low_stock_products) - 3} more"

            count += await _upsert_insight(
                session,
                shop_id=shop_id,
                insight_type="inventory_alert",
                severity="high",
                title=f"{len(low_stock_products)} product{'s' if len(low_stock_products) > 1 else ''} running low on stock",
                action_summary=f"Review inventory for: {names_str}. These products have 5 or fewer units remaining.",
                expected_uplift="Prevent stockout lost revenue",
                confidence=0.95,
                payload={
                    "low_stock_count": len(low_stock_products),
                    "products": [
                        {"id": str(p.id), "title": p.title, "inventory": p.total_inventory}
                        for p in low_stock_products[:5]
                    ],
                },
                admin_deep_link="/products?inventory_quantity_max=5",
            )

        await session.flush()
        logger.info("Insights generated", shop_id=str(shop_id), count=count)

    except Exception as e:
        logger.error("Insight generation failed", error=str(e), shop_id=str(shop_id))

    return count


async def _upsert_insight(
    session: AsyncSession,
    shop_id: UUID,
    insight_type: str,
    severity: str,
    title: str,
    action_summary: str,
    expected_uplift: str,
    confidence: float,
    payload: dict,
    admin_deep_link: str | None = None,
) -> int:
    """
    Create a new insight, replacing any existing active insight of the same type.
    Returns 1 if created, 0 if skipped.
    """
    # Check if an active insight of this type already exists
    existing_stmt = select(Insight).where(
        Insight.shop_id == shop_id,
        Insight.type == insight_type,
        Insight.dismissed_at.is_(None),
    )
    existing_result = await session.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Update existing insight with fresh data
        existing.title = title
        existing.action_summary = action_summary
        existing.expected_uplift = expected_uplift
        existing.confidence = confidence
        existing.payload = payload
        existing.admin_deep_link = admin_deep_link
        existing.severity = severity
        return 0  # Updated, not created

    # Create new insight
    insight = Insight(
        shop_id=shop_id,
        type=insight_type,
        severity=severity,
        title=title,
        action_summary=action_summary,
        expected_uplift=expected_uplift,
        confidence=confidence,
        payload=payload,
        admin_deep_link=admin_deep_link,
    )
    session.add(insight)
    return 1
