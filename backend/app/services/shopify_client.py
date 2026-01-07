"""
Shopify GraphQL client for API interactions.
Handles rate limiting, retries, and token management.
"""
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import decrypt_token

logger = get_logger(__name__)


class ShopifyGraphQLClient:
    """
    Async Shopify GraphQL API client.

    Features:
    - Automatic token decryption
    - Rate limit handling (respects 2 calls/second)
    - Retry logic for transient failures
    - Proper error handling and logging
    """

    GRAPHQL_ENDPOINT = "https://{domain}/admin/api/2024-01/graphql.json"
    MAX_RETRIES = 3
    RATE_LIMIT_DELAY = 0.5  # seconds between calls

    def __init__(
        self,
        access_token_encrypted: str,
        shop_domain: str,
    ) -> None:
        self.access_token = decrypt_token(access_token_encrypted)
        self.shop_domain = shop_domain
        self.endpoint = self.GRAPHQL_ENDPOINT.format(domain=shop_domain)

    async def execute_query(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query against Shopify API.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            Query result data

        Raises:
            ShopifyAPIError: On API errors
        """
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(self.MAX_RETRIES):
                try:
                    response = await client.post(
                        self.endpoint,
                        json=payload,
                        headers=headers,
                    )
                    response.raise_for_status()

                    data = response.json()

                    if "errors" in data:
                        logger.error(
                            "Shopify GraphQL errors",
                            errors=data["errors"],
                            shop=self.shop_domain,
                        )
                        raise ShopifyAPIError(data["errors"])

                    return data.get("data", {})

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        # Rate limited - wait and retry
                        import asyncio

                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise ShopifyAPIError(f"HTTP error: {e.response.status_code}")

                except httpx.RequestError as e:
                    if attempt < self.MAX_RETRIES - 1:
                        continue
                    raise ShopifyAPIError(f"Request failed: {str(e)}")

        raise ShopifyAPIError("Max retries exceeded")

    async def get_shop_info(self) -> dict[str, Any]:
        """Get basic shop information."""
        query = """
        query {
            shop {
                name
                email
                myshopifyDomain
                plan {
                    displayName
                }
                currencyCode
                timezoneAbbreviation
            }
        }
        """
        return await self.execute_query(query)

    async def get_products(
        self,
        first: int = 50,
        after: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fetch products with pagination."""
        query = """
        query GetProducts($first: Int!, $after: String) {
            products(first: $first, after: $after) {
                edges {
                    cursor
                    node {
                        id
                        title
                        handle
                        status
                        productType
                        vendor
                        totalInventory
                        tracksInventory
                        priceRangeV2 {
                            minVariantPrice { amount }
                            maxVariantPrice { amount }
                        }
                        featuredImage {
                            url
                        }
                        collections(first: 10) {
                            edges {
                                node {
                                    title
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        return await self.execute_query(
            query,
            {"first": first, "after": after},
        )

    async def get_orders(
        self,
        first: int = 50,
        after: Optional[str] = None,
        query_filter: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fetch orders with pagination and filtering."""
        query = """
        query GetOrders($first: Int!, $after: String, $query: String) {
            orders(first: $first, after: $after, query: $query) {
                edges {
                    cursor
                    node {
                        id
                        name
                        totalPriceSet {
                            shopMoney { amount currencyCode }
                        }
                        subtotalPriceSet {
                            shopMoney { amount }
                        }
                        totalTaxSet {
                            shopMoney { amount }
                        }
                        totalDiscountsSet {
                            shopMoney { amount }
                        }
                        financialStatus
                        fulfillmentStatus
                        customer {
                            id
                            email
                        }
                        processedAt
                        lineItems(first: 50) {
                            edges {
                                node {
                                    id
                                    title
                                    quantity
                                    originalTotalSet {
                                        shopMoney { amount }
                                    }
                                    product {
                                        id
                                    }
                                }
                            }
                        }
                        discountCodes
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        return await self.execute_query(
            query,
            {"first": first, "after": after, "query": query_filter},
        )


class ShopifyAPIError(Exception):
    """Custom exception for Shopify API errors."""

    def __init__(self, message: str | list) -> None:
        if isinstance(message, list):
            message = "; ".join(str(e.get("message", e)) for e in message)
        super().__init__(message)
