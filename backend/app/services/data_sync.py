"""
Data sync service - pulls products and orders from Shopify GraphQL API
and upserts them into the PostgreSQL database.
"""
import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.order import Order
from app.models.product import Product
from app.models.shop import Shop
from app.services.shopify_client import ShopifyGraphQLClient, ShopifyAPIError

logger = get_logger(__name__)


async def sync_shop_data(shop_id: UUID, full_sync: bool = False) -> None:
    """
    Pull products and orders from Shopify and upsert into DB.

    Called as a FastAPI BackgroundTask from the /shops/{id}/sync endpoint.
    """
    logger.info("Starting data sync", shop_id=str(shop_id), full_sync=full_sync)

    async with get_db_context() as session:
        shop = await session.get(Shop, shop_id)
        if not shop:
            logger.error("Shop not found for sync", shop_id=str(shop_id))
            return

        try:
            client = ShopifyGraphQLClient(
                access_token_encrypted=shop.access_token_encrypted,
                shop_domain=shop.domain,
            )

            # Sync products
            products_synced = await _sync_products(session, client, shop)
            logger.info("Products synced", shop_id=str(shop_id), count=products_synced)

            # Sync orders (last 90 days by default)
            orders_synced = await _sync_orders(session, client, shop)
            logger.info("Orders synced", shop_id=str(shop_id), count=orders_synced)

            # Mark sync complete
            shop.sync_status = "completed"
            shop.last_sync_at = datetime.now(timezone.utc)
            await session.flush()

            logger.info(
                "Data sync completed",
                shop_id=str(shop_id),
                products=products_synced,
                orders=orders_synced,
            )

        except ShopifyAPIError as e:
            logger.error("Shopify API error during sync", error=str(e), shop_id=str(shop_id))
            shop.sync_status = "failed"
            await session.flush()

        except Exception as e:
            logger.error("Unexpected sync error", error=str(e), shop_id=str(shop_id))
            shop.sync_status = "failed"
            await session.flush()


async def _sync_products(
    session,
    client: ShopifyGraphQLClient,
    shop: Shop,
) -> int:
    """Fetch all products from Shopify and upsert into DB."""
    count = 0
    cursor = None

    while True:
        data = await client.get_products(first=50, after=cursor)
        products_data = data.get("products", {})
        edges = products_data.get("edges", [])

        if not edges:
            break

        for edge in edges:
            node = edge["node"]
            cursor = edge["cursor"]

            shopify_gid = node["id"]  # e.g. "gid://shopify/Product/123"

            # Extract price range
            price_range = node.get("priceRangeV2", {})
            price_min = float(price_range.get("minVariantPrice", {}).get("amount", 0))
            price_max = float(price_range.get("maxVariantPrice", {}).get("amount", 0))

            # Extract collections
            collections = [
                edge["node"]["title"]
                for edge in node.get("collections", {}).get("edges", [])
            ]

            # Featured image
            featured_image = node.get("featuredImage")
            image_url = featured_image["url"] if featured_image else None

            # Upsert using raw SQL for ON CONFLICT
            await session.execute(
                text("""
                    INSERT INTO products (id, shop_id, title, handle, status, product_type, vendor,
                        total_inventory, inventory_tracked, price_min, price_max, collections,
                        featured_image_url, synced_at, created_at)
                    VALUES (:id, :shop_id, :title, :handle, :status, :product_type, :vendor,
                        :total_inventory, :inventory_tracked, :price_min, :price_max,
                        :collections::jsonb, :featured_image_url, now(), now())
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        handle = EXCLUDED.handle,
                        status = EXCLUDED.status,
                        product_type = EXCLUDED.product_type,
                        vendor = EXCLUDED.vendor,
                        total_inventory = EXCLUDED.total_inventory,
                        inventory_tracked = EXCLUDED.inventory_tracked,
                        price_min = EXCLUDED.price_min,
                        price_max = EXCLUDED.price_max,
                        collections = EXCLUDED.collections,
                        featured_image_url = EXCLUDED.featured_image_url,
                        synced_at = now()
                """),
                {
                    "id": shopify_gid,
                    "shop_id": shop.id,
                    "title": node.get("title", ""),
                    "handle": node.get("handle", ""),
                    "status": node.get("status", "ACTIVE").lower(),
                    "product_type": node.get("productType"),
                    "vendor": node.get("vendor"),
                    "total_inventory": node.get("totalInventory", 0),
                    "inventory_tracked": node.get("tracksInventory", True),
                    "price_min": price_min,
                    "price_max": price_max,
                    "collections": str(collections).replace("'", '"'),
                    "featured_image_url": image_url,
                },
            )
            count += 1

        # Rate limit: respect Shopify's 2 calls/sec
        await asyncio.sleep(0.5)

        page_info = products_data.get("pageInfo", {})
        if not page_info.get("hasNextPage", False):
            break

    await session.flush()
    return count


async def _sync_orders(
    session,
    client: ShopifyGraphQLClient,
    shop: Shop,
) -> int:
    """Fetch orders from Shopify and upsert into DB."""
    count = 0
    cursor = None

    while True:
        data = await client.get_orders(first=50, after=cursor)
        orders_data = data.get("orders", {})
        edges = orders_data.get("edges", [])

        if not edges:
            break

        for edge in edges:
            node = edge["node"]
            cursor = edge["cursor"]

            shopify_gid = node["id"]  # e.g. "gid://shopify/Order/123"

            # Extract financial data
            total_price = float(
                node.get("totalPriceSet", {}).get("shopMoney", {}).get("amount", 0)
            )
            subtotal_price = float(
                node.get("subtotalPriceSet", {}).get("shopMoney", {}).get("amount", 0)
            )
            total_tax = float(
                node.get("totalTaxSet", {}).get("shopMoney", {}).get("amount", 0)
            )
            total_discounts = float(
                node.get("totalDiscountsSet", {}).get("shopMoney", {}).get("amount", 0)
            )
            currency = (
                node.get("totalPriceSet", {}).get("shopMoney", {}).get("currencyCode", "USD")
            )

            # Customer
            customer = node.get("customer") or {}
            customer_id = customer.get("id")
            customer_email = customer.get("email")

            # Line items
            line_items = []
            for li_edge in node.get("lineItems", {}).get("edges", []):
                li_node = li_edge["node"]
                line_items.append({
                    "id": li_node["id"],
                    "title": li_node["title"],
                    "quantity": li_node["quantity"],
                    "amount": float(
                        li_node.get("originalTotalSet", {})
                        .get("shopMoney", {})
                        .get("amount", 0)
                    ),
                    "product_id": (li_node.get("product") or {}).get("id"),
                })

            # Parse order name to get order number
            order_name = node.get("name", "#0")
            try:
                order_number = int(order_name.replace("#", ""))
            except ValueError:
                order_number = 0

            # Parse processed_at
            processed_at_str = node.get("processedAt", "")
            try:
                processed_at = datetime.fromisoformat(processed_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                processed_at = datetime.now(timezone.utc)

            import json
            line_items_json = json.dumps(line_items)
            discount_codes_json = json.dumps(node.get("discountCodes", []))

            await session.execute(
                text("""
                    INSERT INTO orders (id, shop_id, order_number, name, total_price,
                        subtotal_price, total_tax, total_discounts, currency,
                        financial_status, fulfillment_status, customer_id, customer_email,
                        line_items, line_item_count, discount_codes, processed_at, synced_at)
                    VALUES (:id, :shop_id, :order_number, :name, :total_price,
                        :subtotal_price, :total_tax, :total_discounts, :currency,
                        :financial_status, :fulfillment_status, :customer_id, :customer_email,
                        :line_items::jsonb, :line_item_count, :discount_codes::jsonb,
                        :processed_at, now())
                    ON CONFLICT (id) DO UPDATE SET
                        total_price = EXCLUDED.total_price,
                        subtotal_price = EXCLUDED.subtotal_price,
                        total_tax = EXCLUDED.total_tax,
                        total_discounts = EXCLUDED.total_discounts,
                        financial_status = EXCLUDED.financial_status,
                        fulfillment_status = EXCLUDED.fulfillment_status,
                        line_items = EXCLUDED.line_items,
                        line_item_count = EXCLUDED.line_item_count,
                        discount_codes = EXCLUDED.discount_codes,
                        synced_at = now()
                """),
                {
                    "id": shopify_gid,
                    "shop_id": shop.id,
                    "order_number": order_number,
                    "name": order_name,
                    "total_price": total_price,
                    "subtotal_price": subtotal_price,
                    "total_tax": total_tax,
                    "total_discounts": total_discounts,
                    "currency": currency,
                    "financial_status": node.get("financialStatus", "pending").lower(),
                    "fulfillment_status": (node.get("fulfillmentStatus") or "unfulfilled").lower(),
                    "customer_id": customer_id,
                    "customer_email": customer_email,
                    "line_items": line_items_json,
                    "line_item_count": len(line_items),
                    "discount_codes": discount_codes_json,
                    "processed_at": processed_at,
                },
            )
            count += 1

        # Rate limit
        await asyncio.sleep(0.5)

        page_info = orders_data.get("pageInfo", {})
        if not page_info.get("hasNextPage", False):
            break

    await session.flush()
    return count
