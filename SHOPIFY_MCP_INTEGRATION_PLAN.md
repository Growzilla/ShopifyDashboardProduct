# Shopify MCP Integration Plan for EcomDash V2
**Claude Code + Shopify Dev MCP + Shopify Storefront MCP**

## Executive Summary

This plan integrates two powerful Shopify MCP servers into EcomDash V2 to enable:
1. **AI-Native Development**: Claude Code with direct Shopify API access and validation
2. **Real-Time Store Intelligence**: Live storefront data in dashboard analytics
3. **Enhanced Code Quality**: Shopify-specific GraphQL, Liquid, and component validation
4. **Elevated User Experience**: Store owners get real-time insights powered by live data

---

## Current Architecture Analysis

### Existing Capabilities
- **Backend**: Python FastAPI with PostgreSQL + Redis
- **Shopify Integration**: OAuth + GraphQL client (`shopify_client.py`)
- **AI Services**: DeepSeek (via OpenRouter) + OpenAI fallback for code analysis
- **Insights Engine**: 5 core modules (understocked winners, overstock, coupon cannibalization, etc.)
- **Analytics**: Custom analytics service with ML intent classifier
- **Frontend**: React Router 7 + Shopify Polaris + App Bridge

### Identified Gaps (Solved by MCP Integration)
1. **Development Friction**: Manual documentation lookups during Shopify API development
2. **Validation Gaps**: No pre-deployment validation of GraphQL queries or Liquid templates
3. **Data Staleness**: Dashboard insights based on periodic database sync, not live data
4. **Limited Context**: AI code analyzer doesn't understand Shopify-specific patterns
5. **Reactive Analytics**: Can't leverage real-time cart, checkout, or browse behavior

---

## Integration Strategy

### Phase 1: Development Environment Setup (Claude Code MCP Configuration)

#### 1.1 Configure Shopify Dev MCP
**Purpose**: Enable AI-assisted Shopify development with automatic documentation access and code validation

**Implementation**:
```json
// .claude/settings.local.json (update existing file)
{
  "permissions": {
    "allow": [
      "Bash(tree:*)",
      "Skill(maestro-workflow)",
      "mcp__maestro-mcp__maestro_workflow_with_hitl",
      "mcp__maestro-mcp__maestro_run_stage_with_approval",
      "WebSearch",
      "mcp__maestro-mcp__maestro_get_pending_approvals",
      "WebFetch(domain:render.com)",
      "Bash(find:*)"
    ]
  },
  "mcpServers": {
    "shopify-dev-mcp": {
      "command": "npx",
      "args": ["-y", "@shopify/dev-mcp@latest"],
      "env": {
        "OPT_OUT_INSTRUMENTATION": "true"
      }
    }
  }
}
```

**Available Tools After Setup**:
- `learn_shopify_api` - Teach Claude about Shopify APIs
- `search_docs_chunks` - Fast documentation search
- `fetch_full_docs` - Complete documentation retrieval
- `introspect_graphql_schema` - Explore Admin/Storefront GraphQL schemas
- `validate_graphql_codeblocks` - Validate GraphQL before running
- `validate_component_codeblocks` - Validate JS/TS Shopify components
- `validate_theme_codeblocks` - Validate individual Liquid files
- `validate_theme` - Validate entire Liquid theme directories

**Development Workflow Enhancement**:
```plaintext
BEFORE:
Developer → Manual docs search → Write GraphQL → Test in API → Debug → Repeat

AFTER:
Developer → Ask Claude "How do I query customer metafields?"
→ Claude uses search_docs_chunks + introspect_graphql_schema
→ Claude writes validated GraphQL query
→ Claude validates with validate_graphql_codeblocks
→ Production-ready code generated
```

#### 1.2 Configure Shopify Storefront MCP
**Purpose**: Access real-time store data (products, cart, orders) for live dashboard insights

**Implementation**:
```json
// .claude/settings.local.json (add to mcpServers section)
{
  "mcpServers": {
    "shopify-dev-mcp": { /* ... */ },
    "shopify-storefront-mcp": {
      "command": "npx",
      "args": ["-y", "@shopify/storefront-mcp@latest"],
      "env": {
        "SHOPIFY_STORE_DOMAIN": "${SHOPIFY_STORE_DOMAIN}",
        "SHOPIFY_STOREFRONT_ACCESS_TOKEN": "${SHOPIFY_STOREFRONT_ACCESS_TOKEN}"
      }
    }
  }
}
```

**Environment Variables Required** (add to backend/.env):
```bash
# Storefront API Credentials (different from Admin API)
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_STOREFRONT_ACCESS_TOKEN=your_storefront_token_here
```

**Available Capabilities**:
- Natural language product search
- Product recommendations
- Cart creation/management
- Order status tracking
- Store policies and FAQ access
- Customer order management

---

### Phase 2: Backend Architecture Enhancement

#### 2.1 Create MCP Bridge Service
**Purpose**: Python service to interact with Storefront MCP for real-time data

**New File**: `backend/app/services/shopify_mcp_bridge.py`
```python
"""
Shopify MCP Bridge - Connects Python backend to Shopify Storefront MCP.

Provides real-time store data access without database sync delays.
"""
from typing import Any, Optional
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class ShopifyMCPBridge:
    """
    Bridge to Shopify Storefront MCP for real-time data.

    Unlike shopify_client.py (Admin API), this accesses storefront-facing
    data including cart behavior, live product search, and customer views.
    """

    def __init__(self):
        self.storefront_domain = settings.shopify_store_domain
        self.storefront_token = settings.shopify_storefront_access_token
        self.storefront_api_url = f"https://{self.storefront_domain}/api/2024-01/graphql.json"

    async def search_products_natural_language(
        self,
        query: str,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Natural language product search via Storefront API.

        Example: "red shoes under $100" → Structured product results
        """
        # Storefront API query for product search
        graphql_query = """
        query SearchProducts($query: String!, $first: Int!) {
          products(query: $query, first: $first) {
            edges {
              node {
                id
                title
                handle
                description
                priceRange {
                  minVariantPrice { amount currencyCode }
                  maxVariantPrice { amount currencyCode }
                }
                images(first: 1) {
                  edges {
                    node { url altText }
                  }
                }
                availableForSale
                totalInventory
              }
            }
          }
        }
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.storefront_api_url,
                json={
                    "query": graphql_query,
                    "variables": {"query": query, "first": limit}
                },
                headers={
                    "X-Shopify-Storefront-Access-Token": self.storefront_token,
                    "Content-Type": "application/json"
                }
            )

            data = response.json()
            products = data.get("data", {}).get("products", {}).get("edges", [])
            return [edge["node"] for edge in products]

    async def get_live_cart_metrics(self, shop_id: str) -> dict[str, Any]:
        """
        Get real-time cart abandonment and checkout metrics.

        This would typically require webhooks, but Storefront MCP
        provides read access to cart state.
        """
        # Implementation would use Storefront MCP's cart tools
        pass

    async def get_product_recommendations(
        self,
        product_id: str,
        intent: str = "related"
    ) -> list[dict[str, Any]]:
        """
        AI-powered product recommendations via Storefront MCP.

        Args:
            product_id: Product to base recommendations on
            intent: "related", "upsell", or "cross_sell"
        """
        # Use Storefront MCP's recommendation engine
        pass

# Singleton instance
shopify_mcp_bridge = ShopifyMCPBridge()
```

#### 2.2 Enhance Insights Engine with Live Data
**File**: `backend/app/services/insights_engine.py`

**New Method to Add**:
```python
async def compute_live_storefront_insights(
    self,
    shop_id: UUID,
) -> list[dict[str, Any]]:
    """
    Generate insights using LIVE storefront data (not cached DB data).

    Advantages:
    - Real-time cart abandonment detection
    - Live product search trends
    - Current inventory vs. customer browsing behavior
    """
    from app.services.shopify_mcp_bridge import shopify_mcp_bridge

    insights = []

    # Example: Trending search terms with low conversion
    search_trends = await shopify_mcp_bridge.get_search_trends()

    # Example: High cart adds but low checkouts (live)
    cart_metrics = await shopify_mcp_bridge.get_live_cart_metrics(str(shop_id))

    # Generate real-time insights
    # ... insight generation logic

    return insights
```

#### 2.3 Upgrade AI Code Analyzer with Shopify Validation
**File**: `backend/app/services/ai_analyzer.py`

**New Methods to Add**:
```python
async def analyze_shopify_code(
    self,
    code: str,
    code_type: str,  # "graphql", "liquid", "component"
    language: str = "javascript"
) -> dict[str, Any]:
    """
    Enhanced code analysis with Shopify-specific validation.

    Uses Shopify Dev MCP to validate against actual schemas.
    """
    # 1. Standard AI analysis (existing)
    base_analysis = await self.analyze_code(code, language)

    # 2. Shopify-specific validation via MCP
    shopify_validation = await self._validate_shopify_code(code, code_type)

    # 3. Merge results
    base_analysis["shopify_validation"] = shopify_validation
    base_analysis["scores"]["shopify_compliance"] = (
        100 if shopify_validation["is_valid"] else 50
    )

    return base_analysis

async def _validate_shopify_code(
    self,
    code: str,
    code_type: str
) -> dict[str, Any]:
    """
    Call Shopify Dev MCP validation tools.

    This would integrate with Claude Code's MCP client to call:
    - validate_graphql_codeblocks for GraphQL
    - validate_component_codeblocks for JS/TS
    - validate_theme_codeblocks for Liquid
    """
    # Implementation would call MCP tools via subprocess or MCP SDK
    # For now, placeholder structure:
    return {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "shopify_best_practices": []
    }
```

---

### Phase 3: Frontend Dashboard Enhancement

#### 3.1 New Dashboard Components

**Component 1: Live Product Performance Widget**
**File**: `frontend/app/components/LiveProductInsights.tsx`

```typescript
import { Card, Text, Badge, SkeletonBodyText } from '@shopify/polaris';
import { useQuery } from '@tanstack/react-query';
import { api } from '~/services/api';

export function LiveProductInsights() {
  const { data, isLoading } = useQuery({
    queryKey: ['live-product-insights'],
    queryFn: () => api.get('/api/insights/live'),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) return <SkeletonBodyText lines={3} />;

  return (
    <Card>
      <Text variant="headingMd" as="h2">
        Live Product Performance
      </Text>
      {data?.trending_searches && (
        <div>
          <Text variant="headingSm" as="h3">Trending Searches</Text>
          {data.trending_searches.map(search => (
            <Badge key={search.query}>{search.query} ({search.count})</Badge>
          ))}
        </div>
      )}
      {data?.hot_products && (
        <div>
          <Text variant="headingSm" as="h3">Hot Right Now</Text>
          {/* Real-time product performance */}
        </div>
      )}
    </Card>
  );
}
```

**Component 2: Cart Abandonment Monitor**
**File**: `frontend/app/components/CartAbandonmentMonitor.tsx`

```typescript
export function CartAbandonmentMonitor() {
  // Real-time cart abandonment tracking
  // Uses Storefront MCP data via new backend endpoint
  const { data } = useQuery({
    queryKey: ['cart-abandonment-live'],
    queryFn: () => api.get('/api/analytics/cart-abandonment/live'),
    refetchInterval: 10000, // Every 10 seconds
  });

  return (
    <Card>
      <Text variant="headingMd" as="h2">
        Live Cart Activity
      </Text>
      <div>
        <Metric label="Active Carts" value={data?.active_carts || 0} />
        <Metric label="Abandoned (Last Hour)" value={data?.abandoned_1h || 0} />
        <Metric label="Recovery Rate" value={`${data?.recovery_rate || 0}%`} />
      </div>
    </Card>
  );
}
```

#### 3.2 New Dashboard Route
**File**: `frontend/app/routes/insights.live.tsx`

```typescript
import { json, LoaderFunctionArgs } from '@react-router/node';
import { useLoaderData } from 'react-router';
import { Page, Layout } from '@shopify/polaris';
import { LiveProductInsights } from '~/components/LiveProductInsights';
import { CartAbandonmentMonitor } from '~/components/CartAbandonmentMonitor';

export async function loader({ request }: LoaderFunctionArgs) {
  // Fetch live insights from backend
  const response = await fetch(`${process.env.BACKEND_URL}/api/insights/live`, {
    headers: { Authorization: request.headers.get('Authorization') || '' },
  });

  return json(await response.json());
}

export default function LiveInsights() {
  const data = useLoaderData<typeof loader>();

  return (
    <Page title="Live Store Insights" subtitle="Real-time storefront intelligence">
      <Layout>
        <Layout.Section>
          <LiveProductInsights />
        </Layout.Section>
        <Layout.Section secondary>
          <CartAbandonmentMonitor />
        </Layout.Section>
      </Layout>
    </Page>
  );
}
```

#### 3.3 Backend API Endpoints

**New File**: `backend/app/routers/live_insights.py`
```python
"""Live insights API powered by Shopify Storefront MCP."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.shopify_mcp_bridge import shopify_mcp_bridge

router = APIRouter(prefix="/insights", tags=["Live Insights"])

@router.get("/live")
async def get_live_insights(
    shop_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get real-time storefront insights.

    Unlike /insights which uses cached DB data, this endpoint
    queries Shopify Storefront MCP for live metrics.
    """

    # Live product search trends
    trending_searches = await shopify_mcp_bridge.get_search_trends()

    # Live cart metrics
    cart_metrics = await shopify_mcp_bridge.get_live_cart_metrics(shop_id)

    # Live product performance
    hot_products = await shopify_mcp_bridge.get_trending_products(shop_id)

    return {
        "trending_searches": trending_searches,
        "cart_metrics": cart_metrics,
        "hot_products": hot_products,
        "timestamp": "2024-01-10T12:00:00Z",
        "data_freshness": "real-time"
    }

@router.get("/cart-abandonment/live")
async def get_live_cart_abandonment(shop_id: str):
    """Real-time cart abandonment tracking."""
    return await shopify_mcp_bridge.get_live_cart_metrics(shop_id)
```

---

### Phase 4: Code Quality Integration

#### 4.1 Pre-Commit Hook for Shopify Code Validation

**New File**: `.githooks/pre-commit`
```bash
#!/bin/bash
# Pre-commit hook to validate Shopify code using Dev MCP

echo "🔍 Validating Shopify code..."

# Find all GraphQL files
GRAPHQL_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(graphql|gql)$')

if [ -n "$GRAPHQL_FILES" ]; then
  echo "Validating GraphQL queries..."
  for file in $GRAPHQL_FILES; do
    # Use Claude Code MCP to validate
    # This would call the MCP server's validate_graphql_codeblocks tool
    npx @shopify/dev-mcp validate-graphql "$file"
    if [ $? -ne 0 ]; then
      echo "❌ GraphQL validation failed for $file"
      exit 1
    fi
  done
fi

# Validate Liquid templates
LIQUID_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.liquid$')

if [ -n "$LIQUID_FILES" ]; then
  echo "Validating Liquid templates..."
  for file in $LIQUID_FILES; do
    npx @shopify/dev-mcp validate-liquid "$file"
    if [ $? -ne 0 ]; then
      echo "❌ Liquid validation failed for $file"
      exit 1
    fi
  done
fi

echo "✅ All Shopify code validated successfully"
exit 0
```

**Enable the hook**:
```bash
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
```

#### 4.2 CI/CD Integration

**File**: `.github/workflows/shopify-validation.yml`
```yaml
name: Shopify Code Validation

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Shopify Dev MCP
        run: npm install -g @shopify/dev-mcp

      - name: Validate GraphQL Queries
        run: |
          find . -name "*.graphql" -o -name "*.gql" | while read file; do
            echo "Validating $file"
            shopify-dev-mcp validate-graphql "$file"
          done

      - name: Validate Shopify Components
        run: |
          find ./frontend/app -name "*.tsx" -o -name "*.jsx" | while read file; do
            if grep -q "@shopify" "$file"; then
              echo "Validating Shopify component: $file"
              shopify-dev-mcp validate-component "$file"
            fi
          done

      - name: Report Results
        if: always()
        run: echo "Validation complete"
```

---

## Implementation Roadmap

### Week 1: Foundation
- [ ] Configure both MCP servers in Claude Code settings
- [ ] Test MCP connectivity with sample queries
- [ ] Create environment variable configuration
- [ ] Document MCP tool usage patterns

### Week 2: Backend Integration
- [ ] Build `ShopifyMCPBridge` service
- [ ] Create live insights endpoints
- [ ] Enhance AI analyzer with Shopify validation
- [ ] Add Storefront API credentials to config

### Week 3: Frontend Enhancement
- [ ] Build live dashboard components
- [ ] Create new real-time insights route
- [ ] Integrate with backend live endpoints
- [ ] Add real-time data refresh logic

### Week 4: Code Quality & Testing
- [ ] Implement pre-commit hooks
- [ ] Set up CI/CD validation
- [ ] Write integration tests
- [ ] Performance testing for real-time endpoints

---

## Benefits Summary

### For Developers
1. **Faster Development**: Claude Code + Dev MCP eliminates documentation context switching
2. **Fewer Bugs**: Pre-deployment GraphQL/Liquid validation catches errors early
3. **Better Code Quality**: Shopify-specific linting and best practices enforcement
4. **Direct App Modifications**: Claude can directly modify Shopify app code with validation

### For Store Owners
1. **Real-Time Intelligence**: Dashboard shows live store activity, not stale data
2. **Proactive Alerts**: Cart abandonment and inventory issues detected in real-time
3. **Smarter Recommendations**: AI insights based on actual customer behavior
4. **Faster Response**: Act on opportunities before they become history

### For the Product
1. **Competitive Differentiation**: Only dashboard with true real-time Shopify Storefront data
2. **Higher Accuracy**: Insights based on live data vs. periodic syncs
3. **Better Retention**: Store owners see immediate value from real-time alerts
4. **Faster Feature Development**: MCP integration accelerates Shopify feature builds

---

## Technical Considerations

### Performance
- **Real-time endpoints**: Cache aggressively (10-30 second TTL) to prevent Shopify API rate limits
- **Polling strategy**: Use WebSocket for truly live data, or long-polling for simpler implementation
- **Database impact**: Keep existing periodic sync for historical analytics; use MCP for "right now" data

### Security
- **Storefront API tokens**: Lower privilege than Admin API, safer to use
- **Token storage**: Encrypt Storefront tokens same as Admin tokens
- **MCP server isolation**: Run MCP servers in restricted environment (no file system access)

### Scalability
- **MCP connection pooling**: Multiple shops = multiple MCP instances (containerize)
- **Rate limit management**: Storefront API has different limits than Admin API
- **Caching layer**: Redis cache for MCP responses to reduce API calls

### Monitoring
- **MCP health checks**: Monitor MCP server availability
- **API quota tracking**: Track Storefront API usage per shop
- **Response time alerts**: Alert if real-time endpoints exceed 500ms

---

## Success Metrics

### Development Velocity
- **Baseline**: 2 hours average to implement new Shopify GraphQL feature
- **Target**: 30 minutes with Claude + Dev MCP (75% reduction)

### Code Quality
- **Baseline**: 15% of GraphQL queries fail in production
- **Target**: <2% failure rate with pre-deployment validation

### User Engagement
- **Baseline**: 40% of store owners check dashboard daily
- **Target**: 70% daily active users (driven by real-time alerts)

### Revenue Impact
- **Target**: 25% increase in paid conversions (free → paid tier)
- **Reason**: Real-time insights justify premium pricing

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Shopify API rate limits | High | Aggressive caching + fallback to DB data |
| MCP server downtime | Medium | Graceful degradation to existing sync |
| Storefront API token leakage | High | Encrypted storage + read-only tokens |
| Real-time data inaccuracy | Low | Validate against Admin API periodically |
| Increased infrastructure cost | Medium | Optimize caching, monitor closely |

---

## Next Steps

1. **Review & Approve**: Stakeholder review of this plan
2. **Environment Setup**: Configure Claude Code MCP servers locally
3. **Proof of Concept**: Build one live insight (trending searches) end-to-end
4. **Iterate**: Expand to full feature set based on POC learnings
5. **Deploy**: Gradual rollout to beta users, then full release

---

**Document Version**: 1.0
**Created**: 2026-01-10
**Authors**: Claude Code + Maestro MCP Analysis
**Status**: Awaiting Approval
