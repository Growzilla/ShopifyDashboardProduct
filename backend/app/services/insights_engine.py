"""
Insights Engine - AI-powered business intelligence.
Analyzes shop data to generate actionable insights.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.insight import InsightSeverity, InsightType
from app.models.order import Order
from app.models.product import Product

logger = get_logger(__name__)


class InsightsEngine:
    """
    Engine for computing and generating AI-powered insights.

    Implements the 5 core insight modules:
    1. Traffic-Sales Mismatch
    2. Under-stocked Winners
    3. Over-stock Slow Movers
    4. Coupon Cannibalization
    5. Checkout Drop-off Rise
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def compute_all_insights(
        self,
        shop_id: UUID,
    ) -> list[dict[str, Any]]:
        """Compute all insight types for a shop."""
        insights: list[dict[str, Any]] = []

        # Gather data
        products = await self._get_products(shop_id)
        orders = await self._get_recent_orders(shop_id, days=30)

        if not products or not orders:
            logger.info("Insufficient data for insights", shop_id=str(shop_id))
            return []

        # Compute each insight type
        insights.extend(await self._compute_understocked_winners(shop_id, products, orders))
        insights.extend(await self._compute_overstock_slow_movers(shop_id, products, orders))
        insights.extend(await self._compute_coupon_cannibalization(shop_id, orders))

        logger.info(
            "Computed insights",
            shop_id=str(shop_id),
            count=len(insights),
        )

        return insights

    async def _get_products(self, shop_id: UUID) -> list[Product]:
        """Get all products for a shop."""
        stmt = select(Product).where(Product.shop_id == shop_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_recent_orders(
        self,
        shop_id: UUID,
        days: int,
    ) -> list[Order]:
        """Get orders from the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = select(Order).where(
            Order.shop_id == shop_id,
            Order.processed_at >= cutoff,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _compute_understocked_winners(
        self,
        shop_id: UUID,
        products: list[Product],
        orders: list[Order],
    ) -> list[dict[str, Any]]:
        """
        Identify products with high sales velocity but low inventory.

        Trigger: < 7 days inventory remaining AND sales > P50 percentile
        """
        insights = []

        # Calculate sales velocity per product
        sales_by_product: dict[str, int] = {}
        for order in orders:
            for item in order.line_items or []:
                product_id = item.get("product", {}).get("id")
                if product_id:
                    sales_by_product[product_id] = (
                        sales_by_product.get(product_id, 0) + item.get("quantity", 0)
                    )

        # Find P50 sales threshold
        if not sales_by_product:
            return []

        sales_values = list(sales_by_product.values())
        sales_values.sort()
        p50_threshold = sales_values[len(sales_values) // 2]

        # Check each product
        for product in products:
            sales = sales_by_product.get(product.id, 0)
            if sales < p50_threshold:
                continue

            # Calculate days of inventory remaining
            daily_sales = sales / 30
            if daily_sales <= 0:
                continue

            days_remaining = product.total_inventory / daily_sales

            if days_remaining < 7:
                insights.append({
                    "type": InsightType.UNDERSTOCKED_WINNER.value,
                    "severity": InsightSeverity.HIGH.value,
                    "title": f"Low stock alert: {product.title[:50]}",
                    "action_summary": (
                        f"Only {product.total_inventory} units left "
                        f"(~{days_remaining:.0f} days). Consider restocking or "
                        "enabling pre-orders to avoid stockout."
                    ),
                    "expected_uplift": "Prevent stockout revenue loss",
                    "confidence": 0.85,
                    "payload": {
                        "product_id": product.id,
                        "product_title": product.title,
                        "current_inventory": product.total_inventory,
                        "daily_sales": round(daily_sales, 2),
                        "days_remaining": round(days_remaining, 1),
                    },
                    "admin_deep_link": f"/products/{product.id.split('/')[-1]}",
                })

        return insights

    async def _compute_overstock_slow_movers(
        self,
        shop_id: UUID,
        products: list[Product],
        orders: list[Order],
    ) -> list[dict[str, Any]]:
        """
        Find products with low sales but high inventory (dead stock).

        Trigger: Sales < P20 percentile AND inventory > P80 percentile
        """
        insights = []

        # Calculate metrics
        sales_by_product: dict[str, int] = {}
        for order in orders:
            for item in order.line_items or []:
                product_id = item.get("product", {}).get("id")
                if product_id:
                    sales_by_product[product_id] = (
                        sales_by_product.get(product_id, 0) + item.get("quantity", 0)
                    )

        # Calculate percentiles
        inventories = [p.total_inventory for p in products if p.total_inventory > 0]
        sales_values = [sales_by_product.get(p.id, 0) for p in products]

        if not inventories or not sales_values:
            return []

        inventories.sort()
        sales_values.sort()

        p80_inventory = inventories[int(len(inventories) * 0.8)] if inventories else 0
        p20_sales = sales_values[int(len(sales_values) * 0.2)] if sales_values else 0

        # Find overstock slow movers
        for product in products:
            sales = sales_by_product.get(product.id, 0)
            if (
                product.total_inventory > p80_inventory
                and sales <= p20_sales
            ):
                insights.append({
                    "type": InsightType.OVERSTOCK_SLOW_MOVER.value,
                    "severity": InsightSeverity.MEDIUM.value,
                    "title": f"Dead stock detected: {product.title[:50]}",
                    "action_summary": (
                        f"{product.total_inventory} units in stock but only "
                        f"{sales} sold in 30 days. Consider BOGO offers, "
                        "bundling, or targeted discounts to move inventory."
                    ),
                    "expected_uplift": "Clear dead stock value",
                    "confidence": 0.75,
                    "payload": {
                        "product_id": product.id,
                        "product_title": product.title,
                        "current_inventory": product.total_inventory,
                        "units_sold_30d": sales,
                    },
                    "admin_deep_link": f"/products/{product.id.split('/')[-1]}",
                })

        return insights

    async def _compute_coupon_cannibalization(
        self,
        shop_id: UUID,
        orders: list[Order],
    ) -> list[dict[str, Any]]:
        """
        Detect high discount usage on already popular products.

        Trigger: Discount rate > 40% AND sales > P60 percentile
        """
        insights = []

        # Calculate discount metrics per product
        product_metrics: dict[str, dict] = {}

        for order in orders:
            for item in order.line_items or []:
                product_id = item.get("product", {}).get("id")
                if not product_id:
                    continue

                if product_id not in product_metrics:
                    product_metrics[product_id] = {
                        "title": item.get("title", "Unknown"),
                        "total_revenue": 0,
                        "discounted_orders": 0,
                        "total_orders": 0,
                    }

                revenue = float(
                    item.get("originalTotalSet", {})
                    .get("shopMoney", {})
                    .get("amount", 0)
                )
                product_metrics[product_id]["total_revenue"] += revenue
                product_metrics[product_id]["total_orders"] += 1

                if order.discount_codes:
                    product_metrics[product_id]["discounted_orders"] += 1

        # Find cannibalization
        revenues = [m["total_revenue"] for m in product_metrics.values()]
        if not revenues:
            return []

        revenues.sort()
        p60_revenue = revenues[int(len(revenues) * 0.6)]

        for product_id, metrics in product_metrics.items():
            if metrics["total_orders"] == 0:
                continue

            discount_rate = metrics["discounted_orders"] / metrics["total_orders"]

            if discount_rate > 0.4 and metrics["total_revenue"] > p60_revenue:
                insights.append({
                    "type": InsightType.COUPON_CANNIBALIZATION.value,
                    "severity": InsightSeverity.MEDIUM.value,
                    "title": f"Coupon overuse: {metrics['title'][:50]}",
                    "action_summary": (
                        f"{discount_rate * 100:.0f}% of orders use discounts, "
                        "but this product sells well anyway. Tighten coupon "
                        "eligibility rules to reduce margin leakage."
                    ),
                    "expected_uplift": "Reduce margin leakage",
                    "confidence": 0.7,
                    "payload": {
                        "product_id": product_id,
                        "product_title": metrics["title"],
                        "discount_rate": round(discount_rate, 2),
                        "total_revenue": round(metrics["total_revenue"], 2),
                    },
                    "admin_deep_link": "/discounts",
                })

        return insights
