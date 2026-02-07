# EXECUTION PLAN: Shopify Embedded Admin App
## Lightweight Growzilla-Beta with Multi-Org Support

**Plan Date:** 2026-02-04
**Engineer:** Staff Engineer + Systems Architect
**Ground Truth:** FORENSIC_CODEBASE_ANALYSIS.md
**Reference Implementation:** growzilla-beta/ (working Shopify embedded app)
**Target:** Merchant-installable, Shopify public app approved, multi-store capable

---

## EXECUTIVE SUMMARY

**Current State:** Backend-heavy analytics API with NO Shopify embedded app integration
**Target State:** Lightweight Shopify Admin embedded app (like retail-os/growzilla-beta) that pulls GraphQL data and syncs to backend
**Critical Gap:** Missing OAuth flow, App Bridge, webhooks, and data sync implementation
**Bloat:** ~30% of codebase (code analysis feature, job queue, AI providers) is unused
**Strategy:** Reuse strong foundations (GraphQL client, Polaris UI, token encryption), remove bloat, implement missing critical path

---

## A) VALUE-TO-REALITY MAPPING

| Value / Non-Negotiable | Current State (Forensic) | Delta & Required Changes |
|------------------------|-------------------------|--------------------------|
| **Shopify Admin embedded app with App Bridge** | ❌ NO App Bridge SDK. Frontend is standalone web app (`frontend/app/root.tsx` has Polaris but no App Bridge) | **MUST ADD:** `@shopify/app-bridge-react`, session token handling, TitleBar, embedded navigation. Reference: `growzilla-beta/app/shopify.server.ts` + routes |
| **OAuth install flow for merchant onboarding** | ❌ NO OAuth routes. Code references "auth-proxy" that doesn't exist (`backend/app/routers/shops.py:42`) | **MUST IMPLEMENT:** OAuth callback handler in backend OR migrate to full React Router Shopify template like growzilla-beta (recommended). Reference: `growzilla-beta/app/routes/auth.$.tsx` |
| **Data sync via Shopify GraphQL** | ✅ GraphQL client exists (`backend/app/services/shopify_client.py`) but 🔴 `sync_shop_data()` function missing (`backend/app/routers/shops.py:130` broken import) | **MUST IMPLEMENT:** `backend/app/services/data_sync.py` with incremental cursor tracking. Add `last_products_cursor`, `last_orders_cursor` to shops table |
| **Webhooks for real-time updates** | ✅ HMAC verification exists (`backend/app/core/security.py:89`) but ❌ NO webhook routes | **MUST ADD:** `backend/app/routers/webhooks.py` with handlers for `app/uninstalled`, `orders/create`, `orders/updated`, `products/update`. Reference: `growzilla-beta/app/routes/webhooks.*` |
| **Shopify-Admin-like dashboard (minimal cards)** | ✅ Polaris UI components correct (`frontend/app/routes/_index.tsx`) but NOT embedded | **MUST PRESERVE:** Existing dashboard layout. **MUST WRAP:** with App Bridge Provider, use Shopify Link components |
| **Preserve Growzilla-Beta layout + Insights pages** | ✅ Dashboard exists, ✅ Insights API exists (`backend/app/routers/insights.py`) | **NO CHANGE:** Keep existing routes/components. Just add App Bridge wrapper |
| **Multi-store/org grouping** | ❌ Single tenant only. One shop = one tenant. No `organizations` table | **MUST ADD:** `organizations`, `organization_members` tables. Add `organization_id` to shops (nullable). Store switcher UI. Minimal RBAC (owner/viewer roles) |
| **Minimal scopes for fast public app approval** | ⚠️ Growzilla-beta uses 6 scopes (`read_products,read_orders,read_customers,read_inventory,read_discounts,read_analytics`) | **MUST REDUCE:** Start with 3 core scopes (`read_products,read_orders,read_inventory`). Defer customers/analytics until needed. Document permission matrix |
| **Remove/quarantine bloat** | 🗑️ ~30% bloat: code analysis (commented out), job queue (unused), AI providers (unused), traffic metrics (dead table) | **MUST DELETE:** Code analysis feature (safe per forensic). **MUST COMMENT OUT:** Job queue, notification service until needed |
| **Fast iteration, no overbuilding** | ⚠️ Repository pattern adds indirection. Redis configured but unused | **KEEP:** Repository pattern (helps testing). **REMOVE:** Redis from docker-compose until caching needed |

---

## B) CRITICAL PATH MILESTONES

### Milestone 1: Embedded App Foundation (App Bridge + Session Tokens)
**Objective:** Frontend becomes true Shopify embedded app, validates session tokens

**Deliverables:**
- Frontend wraps all routes with App Bridge Provider
- Session token validation on every API request
- Shopify-native navigation (TitleBar, Link components)
- Embedded app loads in Shopify Admin iframe

**Success Criteria:**
- App loads at `https://{shop}.myshopify.com/admin/apps/{app-handle}`
- Session token extracted from URL and validated
- Navigation uses App Bridge (no full page reloads)

---

### Milestone 2: OAuth Install/Callback + Token Persistence
**Objective:** Merchants can install app, backend stores encrypted access token

**Deliverables:**
- OAuth authorization route (`/auth` or `/api/auth/shopify`)
- OAuth callback handler (validates HMAC, exchanges code for token)
- Encrypted token storage (reuse existing `backend/app/core/security.py:33`)
- Shop creation/update (reuse existing `backend/app/routers/shops.py:34`)

**Success Criteria:**
- Merchant clicks install link → redirected to Shopify OAuth
- Merchant approves → callback receives shop domain + access token
- Token encrypted and stored in `shops.access_token_encrypted`
- Shop record created with `domain`, `scopes`

---

### Milestone 3: Data Sync Implementation (Incremental with Cursors)
**Objective:** App can pull products/orders from Shopify, store in DB, avoid rate limits

**Deliverables:**
- Implement `backend/app/services/data_sync.py` with:
  - `sync_products(shop_id)` using cursor pagination
  - `sync_orders(shop_id)` using cursor pagination
- Add `last_products_cursor`, `last_orders_cursor` to `shops` table (migration)
- Update sync endpoint to call new service
- Sync status tracking (`sync_status`, `last_sync_at`)

**Success Criteria:**
- First sync fetches all products/orders (paginated)
- Second sync only fetches new/updated items (incremental)
- Respects 2 req/sec rate limit (reuse existing backoff in GraphQL client)
- `shops.sync_status` updates: "syncing" → "completed" or "failed"

---

### Milestone 4: Webhooks (Uninstall + Data Updates)
**Objective:** App receives real-time updates from Shopify, handles uninstalls

**Deliverables:**
- Create `backend/app/routers/webhooks.py` with handlers:
  - `POST /webhooks/app/uninstalled` → delete shop (GDPR)
  - `POST /webhooks/orders/create` → upsert order
  - `POST /webhooks/orders/updated` → upsert order
  - `POST /webhooks/products/update` → upsert product
- HMAC verification on all webhook requests (reuse `backend/app/core/security.py:89`)
- Idempotency via `webhook_events` table (log processed webhook IDs)
- Webhook registration strategy (document in onboarding guide)

**Success Criteria:**
- Shopify sends `app/uninstalled` → shop deleted + cascade to all data
- Order created in Shopify → webhook updates DB within 30 seconds
- Duplicate webhook (retry) → no duplicate DB records
- Invalid HMAC → 401 response

---

### Milestone 5: Minimal Dashboard Cards (Shopify Admin Style)
**Objective:** Dashboard mirrors Shopify Admin simplicity, backed by real GraphQL data

**Deliverables:**
- Preserve existing `frontend/app/routes/_index.tsx` layout
- Add App Bridge TitleBar with "Dashboard" title
- Ensure stats cards pull real data (not just demo mode)
- Insights card displays ONE actionable insight (existing)
- Revenue chart uses real order data (existing)

**Success Criteria:**
- Dashboard renders inside Shopify Admin iframe
- Stats show real yesterday vs 7-day average (from DB)
- Chart shows real revenue trend (7-day default)
- ONE AI insight displayed prominently

---

### Milestone 6: Multi-Org (Smallest Viable Schema + Store Switcher)
**Objective:** Support agencies/users managing multiple stores under one org

**Deliverables:**
- Database schema changes:
  - `organizations` table (id, name, owner_email, created_at)
  - `organization_members` table (org_id, email, role: owner|admin|viewer)
  - `shops.organization_id` (nullable FK, default NULL for backward compat)
- Backend changes:
  - `GET /api/organizations` → list user's orgs
  - `GET /api/organizations/{id}/shops` → list shops in org
  - `POST /api/organizations` → create org (owner only)
  - `POST /api/organizations/{id}/members` → invite member
- Frontend changes:
  - Store switcher component (dropdown in App Bridge TitleBar)
  - SessionStorage: `current_shop_id` instead of hardcoded demo UUID
  - Filter all queries by selected shop_id

**Success Criteria:**
- User installs app on 3 stores → can switch between them
- Agency creates org → invites team → all see same stores
- Viewer role → read-only dashboard
- Owner role → can manage org members

---

## C) MINIMAL SCOPE/PERMISSIONS MATRIX

### Initial MVP Scopes (Public App Approval Optimized)

| Scope | Why Needed | GraphQL Queries | API Routes | Can Defer? |
|-------|-----------|----------------|------------|------------|
| `read_products` | Fetch product data for inventory insights (understocked winners, overstock slow movers) | `products(first:50)` { id, title, handle, totalInventory, priceRangeV2 } | `GET /api/dashboard/top-products`, Insights engine | ❌ NO - Core feature |
| `read_orders` | Fetch order data for revenue stats, AOV, insights | `orders(first:50, query:"processed_at:>=...")` { id, totalPriceSet, lineItems, processedAt } | `GET /api/dashboard/stats`, `GET /api/dashboard/revenue-chart` | ❌ NO - Core feature |
| `read_inventory` | Track inventory levels for stockout alerts | `inventoryLevels` (via products.variants.inventoryItem) | Insights engine (understocked alerts) | ⚠️ MAYBE - Can use product.totalInventory initially |
| ~~`read_customers`~~ | Customer segmentation, LTV analysis | customers { id, email, ordersCount, totalSpent } | ❌ NOT IMPLEMENTED YET | ✅ YES - Defer to Phase 2 |
| ~~`read_discounts`~~ | Coupon cannibalization insight | discountCodes, discountNodes | Insights engine (existing logic uses order.discount_codes from orders query) | ✅ YES - Already have data from orders |
| ~~`read_analytics`~~ | Traffic data for traffic-sales mismatch insight | `shopifyqlQuery` or Analytics API | ❌ NOT IMPLEMENTED (forensic: insights #4, #5 missing) | ✅ YES - Defer until implemented |

### Recommended Minimal Scope Set (Start)

```
read_products,read_orders
```

**Rationale:**
- Sufficient for revenue dashboard (orders)
- Sufficient for top products (orders.lineItems)
- Sufficient for 2/5 insights (understocked, overstock)
- `read_inventory` already accessible via `products.totalInventory` (no separate scope)
- Defer customers/analytics until features built

### Scope Expansion Plan (Phase 2+)

| Phase | Add Scope | Feature Unlocked |
|-------|-----------|-----------------|
| Phase 2 | `read_customers` | Customer LTV insights, cohort analysis |
| Phase 3 | `read_analytics` | Traffic-sales mismatch, checkout drop-off insights |
| Phase 3 | `read_discounts` | Only if discount API needed (current: order.discountCodes sufficient) |

### Permission Matrix for Public App Submission

**App Listing Description:**
> "GrowZilla provides AI-powered business insights by analyzing your product and order data. We help identify inventory risks, revenue opportunities, and optimization strategies using read-only access to your store data."

**Data Access Justification (for Shopify review):**

| Scope | Justification | Data Retention | User Benefit |
|-------|--------------|----------------|--------------|
| `read_products` | "We analyze product inventory levels to alert you about stockout risks and overstock situations" | Products cached for 24h, refreshed via webhook | Prevent lost sales from stockouts |
| `read_orders` | "We compute revenue trends, average order value, and identify high-performing products from your order history" | Orders synced for last 90 days (configurable) | Data-driven revenue optimization |

---

## D) DETAILED IMPLEMENTATION PLAN (PHASED)

---

### **PHASE 0: PRE-WORK (Bloat Removal & Safety)**

**Objective:** Clean repo before adding new code, reduce noise, improve developer velocity

**Duration:** 2 days

#### Step 0.1: Delete Code Analysis Feature (Safe per Forensic)

**Files to DELETE:**
- `backend/app/models/code_analysis.py`
- `backend/app/routers/code_analysis.py`
- `backend/app/services/ai_analyzer.py`
- `backend/app/services/ml_intent_classifier.py`
- `backend/app/services/deepseek_client.py`
- `backend/tests/test_code_analysis.py`

**Files to MODIFY:**
- `backend/app/main.py` - Remove commented-out imports (lines 17, 23, 103)
- `backend/app/models/__init__.py` - Remove CodeSubmission imports

**DB Migration:**
```python
# backend/alembic/versions/003_remove_code_analysis.py
def upgrade():
    op.drop_table('analysis_results')
    op.drop_table('code_submissions')
    op.drop_table('notification_preferences')
    op.drop_table('traffic_metrics')

def downgrade():
    # Recreate tables if needed (or leave empty - feature unused)
    pass
```

**Risk:** ❌ None (forensic confirms feature commented out, no usage)

**Rollback:** Keep deleted files in git history, can restore if needed

---

#### Step 0.2: Comment Out Unused Services (Keep for Future)

**Files to MODIFY (add `# FUTURE USE:` comment header):**

`backend/app/services/job_queue.py`:
```python
# FUTURE USE: Background job queue for scheduled sync, pattern analysis
# Currently unused - no worker process running
# Uncomment when implementing:
#   - Scheduled daily/hourly sync
#   - Batch insight computation
#   - Email notifications
# NOTE: Requires ARQ worker process in docker-compose.yml

# [existing code commented out or kept]
```

`backend/app/services/notification_service.py`:
```python
# FUTURE USE: Email notifications via Resend API
# Currently unused - no callers in codebase
# Uncomment when implementing:
#   - Critical insight alerts
#   - Sync failure notifications
#   - Weekly summary emails

# [existing code kept]
```

**Files to MODIFY (remove from docker-compose.yml):**
```yaml
# docker-compose.yml - Remove redis service (lines 23-35)
# Keep in comments with "FUTURE USE: Uncomment when caching needed"
```

**Risk:** ⚠️ Low (might need job queue for future background jobs)

**Rollback:** Uncomment code, restore redis in docker-compose

---

#### Step 0.3: Update Config to Reflect Reality

**Files to MODIFY:**

`backend/app/core/config.py`:
```python
# Lines 68-76 - Comment out unused AI provider config
# FUTURE USE: AI providers for advanced insights (sentiment, predictions)
# openai_api_key: Optional[str] = None
# openai_model: str = "gpt-4-turbo-preview"
# openrouter_api_key: Optional[str] = None
# deepseek_model: str = "deepseek/deepseek-chat"
# deepseek_reasoner_model: str = "deepseek/deepseek-reasoner"
# prefer_deepseek: bool = True

# Lines 39-40 - Comment out redis_url
# redis_url: Optional[RedisDsn] = None  # FUTURE USE: Caching + rate limiting
```

**Tests:**
- `pytest backend/tests/` → all pass
- `backend/app/main.py` imports successfully
- API starts without errors

**Smoke Check:**
```bash
cd backend
source .venv/bin/activate
python -c "from app.main import app; print('✅ App imports successfully')"
uvicorn app.main:app --reload --port 8001  # Check startup logs
```

---

### **PHASE 1: EMBEDDED APP FOUNDATION (App Bridge + Session Tokens)**

**Objective:** Frontend becomes true Shopify embedded app

**Duration:** 3 days

---

#### Step 1.1: Install App Bridge Dependencies

**Files to MODIFY:**

`frontend/package.json`:
```json
{
  "dependencies": {
    "@shopify/app-bridge-react": "^4.1.2",
    "@shopify/polaris": "^12.0.0",  // existing
    "react-router": "^7.0.0",  // existing
    // ... rest
  }
}
```

**Commands:**
```bash
cd frontend
npm install @shopify/app-bridge-react
```

**Tests:**
- `npm run build` → succeeds
- No TypeScript errors

---

#### Step 1.2: Wrap App with App Bridge Provider

**Files to MODIFY:**

`frontend/app/root.tsx`:
```typescript
import { AppProvider as PolarisProvider } from "@shopify/polaris";
import { AppProvider } from "@shopify/app-bridge-react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import enTranslations from "@shopify/polaris/locales/en.json";
import "@shopify/polaris/build/esm/styles.css";
import "./styles/global.css";

export default function App() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  );

  // Extract Shopify host from URL params (embedded app standard)
  const [shopifyHost, setShopifyHost] = useState<string>("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const host = params.get("host");
      if (host) {
        setShopifyHost(host);
        sessionStorage.setItem("shopify_host", host);
      } else {
        setShopifyHost(sessionStorage.getItem("shopify_host") || "");
      }
    }
  }, []);

  // App Bridge config
  const appBridgeConfig = {
    apiKey: import.meta.env.VITE_SHOPIFY_API_KEY || "",
    host: shopifyHost,
    forceRedirect: true,
  };

  return (
    <AppProvider config={appBridgeConfig}>
      <QueryClientProvider client={queryClient}>
        <PolarisProvider i18n={enTranslations}>
          <div className="app-container">
            <Outlet />
          </div>
        </PolarisProvider>
      </QueryClientProvider>
    </AppProvider>
  );
}
```

**Files to CREATE:**

`frontend/.env.example`:
```bash
VITE_API_URL=http://localhost:8000
VITE_SHOPIFY_API_KEY=your_shopify_api_key_here
```

`frontend/.env`:
```bash
VITE_API_URL=http://localhost:8000
VITE_SHOPIFY_API_KEY=02e4e67112ab0bf60bbd4de3afbff59e  # From growzilla-beta
```

**Tests:**
- App loads in browser without errors
- Console shows App Bridge initialization
- `window.shopify` object exists (App Bridge global)

---

#### Step 1.3: Add Session Token to API Calls

**Files to MODIFY:**

`frontend/app/services/api.ts`:
```typescript
import { getSessionToken } from "@shopify/app-bridge-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { DashboardStats, PaginatedInsights, RevenueChartData, Insight } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Get session token for authenticated requests
async function getAuthHeaders(): Promise<HeadersInit> {
  // In embedded app, get session token from App Bridge
  if (typeof window !== "undefined" && window.shopify) {
    try {
      const token = await getSessionToken(window.shopify);
      return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      };
    } catch (error) {
      console.error("Failed to get session token:", error);
    }
  }

  return {
    "Content-Type": "application/json",
  };
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers = await getAuthHeaders();

  const response = await fetch(`${API_URL}/api${endpoint}`, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }

  return response.json();
}

// Remove hardcoded DEMO_SHOP_UUID - shop ID comes from session token
// Backend will extract shop from validated token

// Dashboard Stats - shop_id from backend session
export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: () => fetchApi<DashboardStats>(`/dashboard/stats`),
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: typeof window !== "undefined",
  });
}

// Revenue Chart - shop_id from backend session
export function useRevenueChart(period = "7d") {
  return useQuery({
    queryKey: ["dashboard", "revenue-chart", period],
    queryFn: () =>
      fetchApi<RevenueChartData>(`/dashboard/revenue-chart?period=${period}`),
    staleTime: 5 * 60 * 1000,
    enabled: typeof window !== "undefined",
  });
}

// Insights - shop_id from backend session
export function useInsights(page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ["insights", page, pageSize],
    queryFn: () =>
      fetchApi<PaginatedInsights>(`/insights?page=${page}&page_size=${pageSize}`),
    staleTime: 60 * 1000,
    enabled: typeof window !== "undefined",
  });
}

export function useDismissInsight() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (insightId: string) =>
      fetchApi<{ id: string; message: string }>(
        `/insights/${insightId}/dismiss`,
        { method: "POST" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
    },
  });
}

// Dashboard Summary
export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () =>
      fetchApi<{
        stats: DashboardStats;
        revenueChart: RevenueChartData;
        topProducts: Array<{
          id: string;
          title: string;
          revenue: number;
          unitsSold: number;
        }>;
        activeInsightsCount: number;
      }>(`/dashboard/summary`),
    staleTime: 60 * 1000,
    enabled: typeof window !== "undefined",
  });
}
```

**Files to CREATE:**

`frontend/app/types/window.d.ts`:
```typescript
interface Window {
  shopify?: any;  // App Bridge global
}
```

**Tests:**
- API calls include `Authorization: Bearer <token>` header
- Token is valid Shopify session token (JWT format)

---

#### Step 1.4: Update Dashboard with App Bridge TitleBar

**Files to MODIFY:**

`frontend/app/routes/_index.tsx`:
```typescript
import { Page, TitleBar } from "@shopify/app-bridge-react";
import {
  Card,
  Text,
  BlockStack,
  InlineStack,
  InlineGrid,
  Box,
  Banner,
  Badge,
  Icon,
  SkeletonBodyText,
  SkeletonDisplayText,
  Divider,
} from "@shopify/polaris";
// ... rest of imports

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading, error: statsError } = useDashboardStats();
  const { data: insightsData, isLoading: insightsLoading } = useInsights(1, 1);

  const topInsight = insightsData?.items?.[0] ?? null;

  return (
    <>
      <TitleBar title="Dashboard" />
      <Page>
        <BlockStack gap="600">
          {/* Error Banner */}
          {statsError && (
            <Banner tone="critical" title="Unable to load dashboard data">
              <p>Please check your connection and try again.</p>
            </Banner>
          )}

          {/* AI Insight Card */}
          <InsightCard
            insight={topInsight}
            loading={insightsLoading}
            hasError={!!statsError}
          />

          {/* Stats Cards Row */}
          <InlineGrid columns={{ xs: 1, sm: 2, md: 3 }} gap="400">
            {/* ... existing stats cards ... */}
          </InlineGrid>

          {/* Revenue Chart */}
          <Card>
            {/* ... existing revenue chart ... */}
          </Card>

          {/* Performance Summary */}
          {!statsLoading && stats && (
            <Card>
              {/* ... existing performance summary ... */}
            </Card>
          )}
        </BlockStack>
      </Page>
    </>
  );
}
```

**Tests:**
- Dashboard renders with TitleBar
- Title shows "Dashboard" in Shopify Admin
- Navigation uses App Bridge (no full page reloads)

---

#### Step 1.5: Backend Session Token Validation

**Files to CREATE:**

`backend/app/middleware/shopify_auth.py`:
```python
"""
Shopify session token validation middleware.
Validates JWT tokens from Shopify App Bridge.
"""
from typing import Annotated
from fastapi import Depends, HTTPException, Header, status
from jose import JWTError, jwt
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ShopifySession:
    """Validated Shopify session from App Bridge token."""
    def __init__(self, shop: str, user_id: str | None = None):
        self.shop = shop
        self.user_id = user_id


async def validate_session_token(
    authorization: Annotated[str | None, Header()] = None,
) -> ShopifySession:
    """
    Validate Shopify session token from Authorization header.

    Token format: "Bearer <jwt_token>"
    JWT payload: { "dest": "https://shop.myshopify.com", "aud": "api_key", "sub": "user_id", ... }
    """
    if not authorization:
        # Development mode: allow requests without token (demo mode)
        if settings.debug:
            logger.warning("No authorization header, using demo mode")
            return ShopifySession(shop="demo-store.myshopify.com")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization.replace("Bearer ", "")

    try:
        # Decode and validate JWT
        # Shopify session tokens use HMAC SHA256 with API secret
        payload = jwt.decode(
            token,
            settings.shopify_api_secret or "",
            algorithms=["HS256"],
            audience=settings.shopify_api_key,
        )

        # Verify token not expired
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )

        # Extract shop domain from "dest" claim
        dest = payload.get("dest", "")
        shop = dest.replace("https://", "").replace("http://", "")

        if not shop:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing shop",
            )

        user_id = payload.get("sub")

        logger.info("Session validated", shop=shop, user_id=user_id)

        return ShopifySession(shop=shop, user_id=user_id)

    except JWTError as e:
        logger.warning("Invalid session token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid session token: {str(e)}",
        )
```

**Files to MODIFY:**

`backend/app/routers/dashboard.py`:
```python
from app.middleware.shopify_auth import validate_session_token, ShopifySession

# Remove Query parameter shop_id, use session instead

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    session: Annotated[ShopifySession, Depends(validate_session_token)],
    db_session: Annotated[AsyncSession | None, Depends(get_db_session)],
) -> DashboardStats:
    """Get dashboard statistics from validated Shopify session."""
    # Get shop by domain from session token
    if db_session is None:
        return _get_demo_stats()

    shop_repo = ShopRepository(db_session)
    shop = await shop_repo.get_by_domain(session.shop)

    if not shop:
        logger.info("Shop not found, returning demo data", shop=session.shop)
        return _get_demo_stats()

    # Use shop.id for queries
    shop_id = shop.id

    # ... rest of function (use shop_id from DB, not from query param)
```

**API Contract Changes:**
- **BEFORE:** `GET /api/dashboard/stats?shop_id=<uuid>`
- **AFTER:** `GET /api/dashboard/stats` (shop from session token)
- **BEFORE:** Frontend passes shop_id explicitly
- **AFTER:** Frontend sends session token, backend extracts shop

**Tests:**
- Valid token → request succeeds, correct shop extracted
- Expired token → 401 Unauthorized
- Missing token (debug mode) → demo data returned
- Invalid signature → 401 Unauthorized

**Rollback Strategy:**
- Keep shop_id query param as optional fallback
- If session validation fails in production, log error but don't crash

---

### **PHASE 2: OAUTH INSTALL/CALLBACK + TOKEN PERSISTENCE**

**Objective:** Merchants can install app via OAuth, backend stores encrypted token

**Duration:** 2 days

**Decision Point:** Use growzilla-beta pattern (full React Router Shopify template) OR implement OAuth in FastAPI backend

**Recommendation:** **Implement OAuth in FastAPI backend** (simpler, keeps current architecture)

---

#### Step 2.1: Create OAuth Authorization Route

**Files to CREATE:**

`backend/app/routers/auth.py`:
```python
"""
Shopify OAuth flow for app installation.
Handles authorization and callback.
"""
from typing import Annotated
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import RedirectResponse
import hmac
import hashlib
from urllib.parse import urlencode

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import encrypt_token
from app.repositories.shop import ShopRepository
from app.core.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/shopify")
async def shopify_auth_start(
    shop: Annotated[str, Query(description="Shop domain (e.g., store.myshopify.com)")],
) -> RedirectResponse:
    """
    Start Shopify OAuth flow.
    Redirect merchant to Shopify authorization page.
    """
    # Validate shop domain format
    if not shop or not shop.endswith(".myshopify.com"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shop domain",
        )

    # Build authorization URL
    scopes = "read_products,read_orders"  # Minimal scopes
    redirect_uri = f"{settings.app_url}/auth/callback"

    # Generate nonce for CSRF protection
    import secrets
    nonce = secrets.token_urlsafe(32)

    # Store nonce in session (or Redis) - for simplicity, use query param
    # Production: store in Redis with TTL

    params = {
        "client_id": settings.shopify_api_key,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": nonce,
    }

    auth_url = f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"

    logger.info("Starting OAuth flow", shop=shop, redirect_uri=redirect_uri)

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def shopify_auth_callback(
    shop: Annotated[str, Query()],
    code: Annotated[str, Query()],
    hmac_param: Annotated[str, Query(alias="hmac")],
    state: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RedirectResponse:
    """
    OAuth callback - exchange code for access token.
    Verify HMAC, exchange code, store encrypted token.
    """
    # Verify HMAC
    query_string = f"code={code}&shop={shop}&state={state}"
    computed_hmac = hmac.new(
        settings.shopify_api_secret.encode(),
        query_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_hmac, hmac_param):
        logger.error("HMAC verification failed", shop=shop)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="HMAC verification failed",
        )

    # Exchange code for access token
    import httpx

    token_url = f"https://{shop}/admin/oauth/access_token"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            json={
                "client_id": settings.shopify_api_key,
                "client_secret": settings.shopify_api_secret,
                "code": code,
            },
        )

        if response.status_code != 200:
            logger.error("Token exchange failed", shop=shop, status=response.status_code)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to exchange authorization code",
            )

        data = response.json()
        access_token = data.get("access_token")
        scopes = data.get("scope")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No access token returned",
            )

    # Encrypt and store token
    encrypted_token = encrypt_token(access_token)

    repo = ShopRepository(session)
    shop_obj, created = await repo.create_or_update(
        domain=shop,
        access_token_encrypted=encrypted_token,
        scopes=scopes,
    )

    action = "Installed" if created else "Reinstalled"
    logger.info(f"{action} app", shop=shop, scopes=scopes)

    # Redirect to app with embedded=1 to trigger App Bridge
    app_url = f"https://{shop}/admin/apps/{settings.shopify_app_handle}"

    return RedirectResponse(url=app_url)
```

**Files to MODIFY:**

`backend/app/core/config.py`:
```python
# Add new settings
shopify_app_handle: str = "growzilla-beta"  # From Partner Dashboard
app_url: str = "https://growzilla-app.onrender.com"  # Your app URL
```

`backend/app/main.py`:
```python
from app.routers import (
    auth_router,  # NEW
    dashboard_router,
    health_router,
    insights_router,
    shops_router,
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)  # NEW - no /api prefix (OAuth uses /auth)
app.include_router(shops_router, prefix="/api")
# ...
```

**Tests:**
- Navigate to `/auth/shopify?shop=demo.myshopify.com` → redirects to Shopify OAuth
- Complete OAuth → callback receives code
- Token exchanged and encrypted
- Shop record created/updated in DB

---

#### Step 2.2: Register Webhooks After Install

**Files to MODIFY:**

`backend/app/routers/auth.py` (callback function):
```python
# After storing shop, register webhooks
from app.services.webhook_registration import register_all_webhooks

# ... (after shop created) ...

# Register webhooks
try:
    await register_all_webhooks(shop_obj)
    logger.info("Webhooks registered", shop=shop)
except Exception as e:
    logger.error("Failed to register webhooks", shop=shop, error=str(e))
    # Don't fail install, just log error
```

**Files to CREATE:**

`backend/app/services/webhook_registration.py`:
```python
"""
Webhook registration service.
Registers Shopify webhooks after app installation.
"""
from app.models.shop import Shop
from app.core.config import settings
from app.core.logging import get_logger
from app.services.shopify_client import ShopifyGraphQLClient

logger = get_logger(__name__)


async def register_all_webhooks(shop: Shop) -> None:
    """Register all required webhooks for a shop."""
    client = ShopifyGraphQLClient(
        access_token_encrypted=shop.access_token_encrypted,
        shop_domain=shop.domain,
    )

    webhooks = [
        {
            "topic": "APP_UNINSTALLED",
            "endpoint": f"{settings.app_url}/webhooks/app/uninstalled",
        },
        {
            "topic": "ORDERS_CREATE",
            "endpoint": f"{settings.app_url}/webhooks/orders/create",
        },
        {
            "topic": "ORDERS_UPDATED",
            "endpoint": f"{settings.app_url}/webhooks/orders/updated",
        },
        {
            "topic": "PRODUCTS_UPDATE",
            "endpoint": f"{settings.app_url}/webhooks/products/update",
        },
    ]

    for webhook in webhooks:
        try:
            mutation = """
            mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
              webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
                webhookSubscription {
                  id
                  topic
                  endpoint {
                    __typename
                    ... on WebhookHttpEndpoint {
                      callbackUrl
                    }
                  }
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """

            variables = {
                "topic": webhook["topic"],
                "webhookSubscription": {
                    "callbackUrl": webhook["endpoint"],
                    "format": "JSON",
                },
            }

            result = await client.execute_query(mutation, variables)

            errors = result.get("webhookSubscriptionCreate", {}).get("userErrors", [])
            if errors:
                logger.error("Webhook registration error", topic=webhook["topic"], errors=errors)
            else:
                logger.info("Webhook registered", topic=webhook["topic"], endpoint=webhook["endpoint"])

        except Exception as e:
            logger.error("Failed to register webhook", topic=webhook["topic"], error=str(e))
            # Continue registering other webhooks
```

**Tests:**
- Install app → webhooks registered
- Check Shopify Admin → Settings → Notifications → Webhooks shows 4 subscriptions
- Webhook delivery sends to correct URLs

---

### **PHASE 3: DATA SYNC IMPLEMENTATION**

**Objective:** Implement missing `sync_shop_data()`, add incremental cursors

**Duration:** 3 days

---

#### Step 3.1: Database Migration - Add Sync Cursors

**Files to CREATE:**

`backend/alembic/versions/004_add_sync_cursors.py`:
```python
"""Add sync cursor tracking to shops table

Revision ID: 004_add_sync_cursors
Revises: 003_remove_code_analysis
Create Date: 2026-02-04
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = '004_add_sync_cursors'
down_revision: Union[str, None] = '003_remove_code_analysis'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cursor tracking columns
    op.add_column('shops', sa.Column('last_products_cursor', sa.String(255), nullable=True))
    op.add_column('shops', sa.Column('last_orders_cursor', sa.String(255), nullable=True))
    op.add_column('shops', sa.Column('last_products_sync_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('shops', sa.Column('last_orders_sync_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('shops', sa.Column('sync_error_message', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('shops', 'last_products_cursor')
    op.drop_column('shops', 'last_orders_cursor')
    op.drop_column('shops', 'last_products_sync_at')
    op.drop_column('shops', 'last_orders_sync_at')
    op.drop_column('shops', 'sync_error_message')
```

**Files to MODIFY:**

`backend/app/models/shop.py`:
```python
# Add new fields
last_products_cursor: Mapped[Optional[str]] = mapped_column(
    String(255),
    nullable=True,
)
last_orders_cursor: Mapped[Optional[str]] = mapped_column(
    String(255),
    nullable=True,
)
last_products_sync_at: Mapped[Optional[datetime]] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
)
last_orders_sync_at: Mapped[Optional[datetime]] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
)
sync_error_message: Mapped[Optional[str]] = mapped_column(
    Text,
    nullable=True,
)
```

**Run Migration:**
```bash
cd backend
alembic upgrade head
```

---

#### Step 3.2: Implement Data Sync Service

**Files to CREATE:**

`backend/app/services/data_sync.py`:
```python
"""
Shopify data synchronization service.
Implements incremental sync with cursor-based pagination.
"""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.models.shop import Shop
from app.models.product import Product
from app.models.order import Order
from app.repositories.shop import ShopRepository
from app.services.shopify_client import ShopifyGraphQLClient, ShopifyAPIError

logger = get_logger(__name__)


async def sync_shop_data(
    shop_id: UUID,
    full_sync: bool = False,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Sync products and orders for a shop from Shopify GraphQL API.

    Args:
        shop_id: Shop UUID
        full_sync: If True, ignore cursors and fetch all data
        session: DB session (optional, will create if not provided)

    Returns:
        Sync result summary
    """
    if session is None:
        from app.core.database import get_db_session
        async for sess in get_db_session():
            session = sess
            break

    if session is None:
        raise ValueError("No database session available")

    # Get shop
    repo = ShopRepository(session)
    shop = await repo.get_by_id(shop_id)

    if not shop:
        raise ValueError(f"Shop not found: {shop_id}")

    # Update sync status
    await repo.update_sync_status(shop, "syncing")

    client = ShopifyGraphQLClient(
        access_token_encrypted=shop.access_token_encrypted,
        shop_domain=shop.domain,
    )

    result = {
        "shop_id": str(shop_id),
        "shop_domain": shop.domain,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "products_synced": 0,
        "orders_synced": 0,
        "errors": [],
    }

    try:
        # Sync products
        products_result = await sync_products(client, shop, session, full_sync)
        result["products_synced"] = products_result["count"]
        result["products_cursor"] = products_result.get("cursor")

        # Sync orders
        orders_result = await sync_orders(client, shop, session, full_sync)
        result["orders_synced"] = orders_result["count"]
        result["orders_cursor"] = orders_result.get("cursor")

        # Update shop sync metadata
        shop.last_sync_at = datetime.now(timezone.utc)
        shop.sync_status = "completed"
        shop.sync_error_message = None

        if products_result.get("cursor"):
            shop.last_products_cursor = products_result["cursor"]
            shop.last_products_sync_at = datetime.now(timezone.utc)

        if orders_result.get("cursor"):
            shop.last_orders_cursor = orders_result["cursor"]
            shop.last_orders_sync_at = datetime.now(timezone.utc)

        await session.commit()

        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        result["status"] = "completed"

        logger.info(
            "Sync completed",
            shop_id=str(shop_id),
            products=result["products_synced"],
            orders=result["orders_synced"],
        )

        return result

    except Exception as e:
        # Update sync status on error
        shop.sync_status = "failed"
        shop.sync_error_message = str(e)
        await session.commit()

        result["status"] = "failed"
        result["error"] = str(e)
        result["completed_at"] = datetime.now(timezone.utc).isoformat()

        logger.error("Sync failed", shop_id=str(shop_id), error=str(e))

        return result


async def sync_products(
    client: ShopifyGraphQLClient,
    shop: Shop,
    session: AsyncSession,
    full_sync: bool,
) -> dict[str, Any]:
    """Sync products with cursor-based pagination."""
    cursor = None if full_sync else shop.last_products_cursor
    count = 0

    while True:
        try:
            # Fetch products page
            data = await client.get_products(first=50, after=cursor)

            products_data = data.get("products", {})
            edges = products_data.get("edges", [])
            page_info = products_data.get("pageInfo", {})

            # Upsert products
            for edge in edges:
                node = edge["node"]
                product_id = node["id"]

                # Check if product exists
                stmt = select(Product).where(
                    Product.shop_id == shop.id,
                    Product.shopify_id == int(product_id.split("/")[-1]),
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update
                    existing.title = node.get("title", "")
                    existing.handle = node.get("handle")
                    existing.product_type = node.get("productType")
                    existing.vendor = node.get("vendor")
                    existing.status = node.get("status")
                    existing.total_inventory = node.get("totalInventory", 0)

                    price_range = node.get("priceRangeV2", {})
                    min_price = price_range.get("minVariantPrice", {}).get("amount")
                    max_price = price_range.get("maxVariantPrice", {}).get("amount")

                    if min_price:
                        existing.price_min = float(min_price)
                    if max_price:
                        existing.price_max = float(max_price)

                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    # Insert
                    product = Product(
                        shop_id=shop.id,
                        shopify_id=int(product_id.split("/")[-1]),
                        title=node.get("title", ""),
                        handle=node.get("handle"),
                        product_type=node.get("productType"),
                        vendor=node.get("vendor"),
                        status=node.get("status"),
                        total_inventory=node.get("totalInventory", 0),
                    )

                    price_range = node.get("priceRangeV2", {})
                    min_price = price_range.get("minVariantPrice", {}).get("amount")
                    max_price = price_range.get("maxVariantPrice", {}).get("amount")

                    if min_price:
                        product.price_min = float(min_price)
                    if max_price:
                        product.price_max = float(max_price)

                    session.add(product)

                count += 1

            await session.commit()

            # Check if more pages
            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")

        except ShopifyAPIError as e:
            logger.error("Product sync error", shop_id=str(shop.id), error=str(e))
            raise

    return {"count": count, "cursor": cursor}


async def sync_orders(
    client: ShopifyGraphQLClient,
    shop: Shop,
    session: AsyncSession,
    full_sync: bool,
) -> dict[str, Any]:
    """Sync orders with cursor-based pagination."""
    cursor = None if full_sync else shop.last_orders_cursor
    count = 0

    # Only fetch orders from last 90 days (or all if full_sync)
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    query_filter = None if full_sync else f"processed_at:>='{cutoff.isoformat()}'"

    while True:
        try:
            # Fetch orders page
            data = await client.get_orders(first=50, after=cursor, query_filter=query_filter)

            orders_data = data.get("orders", {})
            edges = orders_data.get("edges", [])
            page_info = orders_data.get("pageInfo", {})

            # Upsert orders
            for edge in edges:
                node = edge["node"]
                order_id = node["id"]

                # Check if order exists
                stmt = select(Order).where(
                    Order.shop_id == shop.id,
                    Order.shopify_id == int(order_id.split("/")[-1]),
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                # Extract line items
                line_items = []
                for item_edge in node.get("lineItems", {}).get("edges", []):
                    item_node = item_edge["node"]
                    line_items.append({
                        "id": item_node.get("id"),
                        "title": item_node.get("title"),
                        "quantity": item_node.get("quantity"),
                        "product": item_node.get("product"),
                        "originalTotalSet": item_node.get("originalTotalSet"),
                    })

                total_price = float(
                    node.get("totalPriceSet", {})
                    .get("shopMoney", {})
                    .get("amount", 0)
                )
                subtotal_price = float(
                    node.get("subtotalPriceSet", {})
                    .get("shopMoney", {})
                    .get("amount", 0)
                )
                total_tax = float(
                    node.get("totalTaxSet", {})
                    .get("shopMoney", {})
                    .get("amount", 0)
                )
                total_discounts = float(
                    node.get("totalDiscountsSet", {})
                    .get("shopMoney", {})
                    .get("amount", 0)
                )

                processed_at = node.get("processedAt")
                if processed_at:
                    processed_at = datetime.fromisoformat(processed_at.replace("Z", "+00:00"))

                if existing:
                    # Update
                    existing.order_number = node.get("name")
                    existing.email = node.get("customer", {}).get("email")
                    existing.financial_status = node.get("financialStatus")
                    existing.fulfillment_status = node.get("fulfillmentStatus")
                    existing.total_price = total_price
                    existing.subtotal_price = subtotal_price
                    existing.total_tax = total_tax
                    existing.total_discounts = total_discounts
                    existing.line_items = line_items
                    existing.line_items_count = len(line_items)
                    existing.discount_codes = node.get("discountCodes", [])
                    existing.processed_at = processed_at
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    # Insert
                    order = Order(
                        shop_id=shop.id,
                        shopify_id=int(order_id.split("/")[-1]),
                        order_number=node.get("name"),
                        email=node.get("customer", {}).get("email"),
                        financial_status=node.get("financialStatus"),
                        fulfillment_status=node.get("fulfillmentStatus"),
                        total_price=total_price,
                        subtotal_price=subtotal_price,
                        total_tax=total_tax,
                        total_discounts=total_discounts,
                        line_items=line_items,
                        line_items_count=len(line_items),
                        discount_codes=node.get("discountCodes", []),
                        processed_at=processed_at,
                    )
                    session.add(order)

                count += 1

            await session.commit()

            # Check if more pages
            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")

        except ShopifyAPIError as e:
            logger.error("Order sync error", shop_id=str(shop.id), error=str(e))
            raise

    return {"count": count, "cursor": cursor}
```

**Files to MODIFY:**

`backend/app/models/order.py`:
```python
# Add line_items and discount_codes fields
from sqlalchemy.dialects.postgresql import JSONB

line_items: Mapped[list[dict]] = mapped_column(
    JSONB,
    default=list,
)
discount_codes: Mapped[list[str]] = mapped_column(
    JSONB,
    default=list,
)
```

**Tests:**
- First sync fetches all products (no cursor) → stores cursor
- Second sync uses cursor → fetches only new products
- Order sync respects 90-day window
- Sync status updates correctly (syncing → completed/failed)

---

#### Step 3.3: Update Sync Trigger Endpoint

**Files to MODIFY:**

`backend/app/routers/shops.py`:
```python
# Fix broken import
from app.services.data_sync import sync_shop_data  # Was missing

@router.post("/{shop_id}/sync", response_model=ShopSyncResponse)
async def trigger_sync(
    shop_id: UUID,
    sync_request: ShopSyncRequest,
    background_tasks: BackgroundTasks,
    repo: Annotated[ShopRepository, Depends(get_shop_repository)],
) -> ShopSyncResponse:
    """Trigger a data sync for a shop."""
    shop = await repo.get_by_id(shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found",
        )

    # Mark as syncing
    await repo.update_sync_status(shop, "syncing")

    # Queue background sync (now implemented!)
    background_tasks.add_task(
        sync_shop_data,
        shop_id=shop_id,
        full_sync=sync_request.full_sync,
    )

    logger.info("Sync triggered", shop_id=str(shop_id), full_sync=sync_request.full_sync)

    return ShopSyncResponse(
        message="Sync started",
        shop_id=shop_id,
        sync_started=True,
    )
```

**Tests:**
- POST `/api/shops/{id}/sync` → sync starts
- Background task runs successfully
- Products/orders appear in DB
- Sync status updates

---

### **PHASE 4: WEBHOOKS (Uninstall + Data Updates)**

**Objective:** Receive real-time Shopify webhooks, handle uninstalls, update data

**Duration:** 2 days

---

#### Step 4.1: Create Webhook Router

**Files to CREATE:**

`backend/app/routers/webhooks.py`:
```python
"""
Shopify webhook handlers.
Handles app uninstall, order updates, product updates.
"""
from typing import Annotated
from fastapi import APIRouter, Request, HTTPException, Header, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.core.security import verify_shopify_hmac
from app.core.database import get_db_session
from app.repositories.shop import ShopRepository
from app.models.shop import Shop
from app.models.order import Order
from app.models.product import Product
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def verify_webhook(
    request: Request,
    x_shopify_hmac_sha256: Annotated[str | None, Header()] = None,
) -> bytes:
    """Verify Shopify webhook HMAC and return body."""
    if not x_shopify_hmac_sha256:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing HMAC header",
        )

    body = await request.body()

    if not verify_shopify_hmac(x_shopify_hmac_sha256, body):
        logger.error("Webhook HMAC verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC",
        )

    return body


@router.post("/app/uninstalled")
async def app_uninstalled(
    body: Annotated[bytes, Depends(verify_webhook)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """
    Handle app uninstall webhook.
    Delete shop and all associated data (GDPR compliance).
    """
    import json
    data = json.loads(body)

    shop_domain = data.get("domain") or data.get("myshopify_domain")

    if not shop_domain:
        logger.error("Missing shop domain in uninstall webhook", data=data)
        return {"status": "error", "message": "Missing shop domain"}

    # Get shop
    repo = ShopRepository(session)
    shop = await repo.get_by_domain(shop_domain)

    if not shop:
        logger.warning("Shop not found for uninstall", domain=shop_domain)
        return {"status": "ok", "message": "Shop not found"}

    # Delete shop (cascade deletes all related data)
    await repo.delete(shop)

    logger.info("App uninstalled, shop deleted", domain=shop_domain)

    return {"status": "ok", "message": "Shop deleted"}


@router.post("/orders/create")
async def orders_create(
    body: Annotated[bytes, Depends(verify_webhook)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Handle new order webhook."""
    import json
    data = json.loads(body)

    await upsert_order(data, session)

    return {"status": "ok"}


@router.post("/orders/updated")
async def orders_updated(
    body: Annotated[bytes, Depends(verify_webhook)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Handle order update webhook."""
    import json
    data = json.loads(body)

    await upsert_order(data, session)

    return {"status": "ok"}


@router.post("/products/update")
async def products_update(
    body: Annotated[bytes, Depends(verify_webhook)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Handle product update webhook."""
    import json
    data = json.loads(body)

    await upsert_product(data, session)

    return {"status": "ok"}


async def upsert_order(data: dict, session: AsyncSession) -> None:
    """Upsert order from webhook data."""
    # Get shop by domain
    shop_domain = data.get("shop_domain") or data.get("myshopify_domain")

    repo = ShopRepository(session)
    shop = await repo.get_by_domain(shop_domain)

    if not shop:
        logger.error("Shop not found for order webhook", domain=shop_domain)
        return

    order_id = data.get("id")

    # Check if order exists
    stmt = select(Order).where(
        Order.shop_id == shop.id,
        Order.shopify_id == order_id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    # Extract line items (webhook format different from GraphQL)
    line_items = []
    for item in data.get("line_items", []):
        line_items.append({
            "id": str(item.get("id")),
            "title": item.get("title"),
            "quantity": item.get("quantity"),
            "price": item.get("price"),
            "product_id": str(item.get("product_id")),
        })

    processed_at = data.get("processed_at")
    if processed_at:
        processed_at = datetime.fromisoformat(processed_at.replace("Z", "+00:00"))

    if existing:
        # Update
        existing.order_number = data.get("name")
        existing.email = data.get("email")
        existing.financial_status = data.get("financial_status")
        existing.fulfillment_status = data.get("fulfillment_status")
        existing.total_price = float(data.get("total_price", 0))
        existing.subtotal_price = float(data.get("subtotal_price", 0))
        existing.total_tax = float(data.get("total_tax", 0))
        existing.total_discounts = float(data.get("total_discounts", 0))
        existing.line_items = line_items
        existing.line_items_count = len(line_items)
        existing.discount_codes = [dc.get("code") for dc in data.get("discount_codes", [])]
        existing.processed_at = processed_at
        existing.updated_at = datetime.now(timezone.utc)
    else:
        # Insert
        order = Order(
            shop_id=shop.id,
            shopify_id=order_id,
            order_number=data.get("name"),
            email=data.get("email"),
            financial_status=data.get("financial_status"),
            fulfillment_status=data.get("fulfillment_status"),
            total_price=float(data.get("total_price", 0)),
            subtotal_price=float(data.get("subtotal_price", 0)),
            total_tax=float(data.get("total_tax", 0)),
            total_discounts=float(data.get("total_discounts", 0)),
            line_items=line_items,
            line_items_count=len(line_items),
            discount_codes=[dc.get("code") for dc in data.get("discount_codes", [])],
            processed_at=processed_at,
        )
        session.add(order)

    await session.commit()
    logger.info("Order upserted from webhook", shop_id=str(shop.id), order_id=order_id)


async def upsert_product(data: dict, session: AsyncSession) -> None:
    """Upsert product from webhook data."""
    # Get shop by domain
    shop_domain = data.get("shop_domain") or data.get("myshopify_domain")

    repo = ShopRepository(session)
    shop = await repo.get_by_domain(shop_domain)

    if not shop:
        logger.error("Shop not found for product webhook", domain=shop_domain)
        return

    product_id = data.get("id")

    # Check if product exists
    stmt = select(Product).where(
        Product.shop_id == shop.id,
        Product.shopify_id == product_id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    variants = data.get("variants", [])
    total_inventory = sum(v.get("inventory_quantity", 0) for v in variants)

    if existing:
        # Update
        existing.title = data.get("title", "")
        existing.handle = data.get("handle")
        existing.product_type = data.get("product_type")
        existing.vendor = data.get("vendor")
        existing.status = data.get("status")
        existing.total_inventory = total_inventory
        existing.updated_at = datetime.now(timezone.utc)
    else:
        # Insert
        product = Product(
            shop_id=shop.id,
            shopify_id=product_id,
            title=data.get("title", ""),
            handle=data.get("handle"),
            product_type=data.get("product_type"),
            vendor=data.get("vendor"),
            status=data.get("status"),
            total_inventory=total_inventory,
        )
        session.add(product)

    await session.commit()
    logger.info("Product upserted from webhook", shop_id=str(shop.id), product_id=product_id)
```

**Files to MODIFY:**

`backend/app/main.py`:
```python
from app.routers import (
    auth_router,
    dashboard_router,
    health_router,
    insights_router,
    shops_router,
    webhooks_router,  # NEW
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(webhooks_router)  # NEW - no /api prefix
app.include_router(shops_router, prefix="/api")
# ...
```

**Tests:**
- Send test webhook with valid HMAC → 200 OK
- Send test webhook with invalid HMAC → 401 Unauthorized
- App uninstall webhook → shop deleted from DB
- Order create webhook → order appears in DB
- Product update webhook → product updated in DB

---

#### Step 4.2: Webhook Idempotency (Prevent Duplicates)

**Files to CREATE:**

`backend/alembic/versions/005_webhook_events.py`:
```python
"""Add webhook_events table for idempotency

Revision ID: 005_webhook_events
Revises: 004_add_sync_cursors
Create Date: 2026-02-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '005_webhook_events'
down_revision: Union[str, None] = '004_add_sync_cursors'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shops.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('topic', sa.String(100), nullable=False, index=True),
        sa.Column('shopify_webhook_id', sa.String(255), nullable=True, index=True),
        sa.Column('payload_hash', sa.String(64), nullable=False, index=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('shop_id', 'payload_hash', name='uq_webhook_events_shop_payload'),
    )


def downgrade() -> None:
    op.drop_table('webhook_events')
```

**Files to CREATE:**

`backend/app/models/webhook_event.py`:
```python
"""
Webhook event model for idempotency tracking.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.shop import Shop


class WebhookEvent(Base):
    """Processed webhook event for deduplication."""

    __tablename__ = "webhook_events"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    shop_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    shopify_webhook_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    payload_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    shop: Mapped["Shop"] = relationship("Shop", back_populates="webhook_events")
```

**Files to MODIFY:**

`backend/app/models/shop.py`:
```python
# Add relationship
webhook_events: Mapped[list["WebhookEvent"]] = relationship(
    "WebhookEvent",
    back_populates="shop",
    cascade="all, delete-orphan",
)
```

`backend/app/routers/webhooks.py`:
```python
import hashlib
from app.models.webhook_event import WebhookEvent

async def check_webhook_processed(
    body: bytes,
    shop_id: UUID,
    topic: str,
    session: AsyncSession,
) -> bool:
    """Check if webhook already processed (idempotency)."""
    # Hash payload
    payload_hash = hashlib.sha256(body).hexdigest()

    # Check if exists
    from sqlalchemy import select
    stmt = select(WebhookEvent).where(
        WebhookEvent.shop_id == shop_id,
        WebhookEvent.payload_hash == payload_hash,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        logger.info("Webhook already processed", topic=topic, shop_id=str(shop_id))
        return True

    # Record event
    event = WebhookEvent(
        shop_id=shop_id,
        topic=topic,
        payload_hash=payload_hash,
    )
    session.add(event)
    await session.commit()

    return False

# Update webhook handlers to check idempotency
@router.post("/orders/create")
async def orders_create(
    body: Annotated[bytes, Depends(verify_webhook)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Handle new order webhook."""
    import json
    data = json.loads(body)

    shop_domain = data.get("shop_domain") or data.get("myshopify_domain")
    repo = ShopRepository(session)
    shop = await repo.get_by_domain(shop_domain)

    if not shop:
        return {"status": "error", "message": "Shop not found"}

    # Check idempotency
    if await check_webhook_processed(body, shop.id, "orders/create", session):
        return {"status": "ok", "message": "Already processed"}

    await upsert_order(data, session)

    return {"status": "ok"}
```

**Tests:**
- Send same webhook twice → second returns "Already processed"
- Webhook event recorded in DB
- No duplicate orders created

---

### **PHASE 5: MINIMAL DASHBOARD (Preserve + Wrap with App Bridge)**

**Objective:** Ensure existing dashboard works in embedded app context

**Duration:** 1 day

This phase is mostly DONE - just needs App Bridge wrapper from Phase 1.

**Checklist:**
- ✅ Dashboard layout preserved (`frontend/app/routes/_index.tsx`)
- ✅ Stats cards show real data (from Phase 3 sync)
- ✅ Revenue chart works (existing)
- ✅ ONE insight displayed (existing)
- ✅ App Bridge TitleBar added (Phase 1 Step 1.4)

**Additional Changes:**

`frontend/app/routes/analytics.dashboard.tsx`:
```typescript
import { TitleBar } from "@shopify/app-bridge-react";

export default function AnalyticsDashboard() {
  return (
    <>
      <TitleBar title="Analytics" />
      {/* existing content */}
    </>
  );
}
```

**Tests:**
- All routes have TitleBar
- Navigation uses Polaris Link (not <a>)
- Embedded app renders correctly in Shopify Admin

---

### **PHASE 6: MULTI-ORG (Smallest Viable Schema + Store Switcher)**

**Objective:** Support agencies managing multiple stores

**Duration:** 3 days

---

#### Step 6.1: Database Schema - Organizations

**Files to CREATE:**

`backend/alembic/versions/006_add_organizations.py`:
```python
"""Add organizations and multi-store support

Revision ID: 006_add_organizations
Revises: 005_webhook_events
Create Date: 2026-02-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '006_add_organizations'
down_revision: Union[str, None] = '005_webhook_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_email', sa.String(255), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Organization members table
    op.create_table(
        'organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('role', sa.String(20), nullable=False, default='viewer'),  # owner, admin, viewer
        sa.Column('invited_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('organization_id', 'email', name='uq_org_members_org_email'),
    )

    # Add organization_id to shops (nullable for backward compat)
    op.add_column('shops', sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column('shops', 'organization_id')
    op.drop_table('organization_members')
    op.drop_table('organizations')
```

**Files to CREATE:**

`backend/app/models/organization.py`:
```python
"""
Organization model for multi-store grouping.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.organization_member import OrganizationMember


class Organization(Base):
    """Organization for grouping multiple shops."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    owner_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    shops: Mapped[list["Shop"]] = relationship(
        "Shop",
        back_populates="organization",
    )
    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
```

`backend/app/models/organization_member.py`:
```python
"""
Organization member model for access control.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class OrganizationMember(Base):
    """Organization member with role-based access."""

    __tablename__ = "organization_members"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="viewer",
    )  # owner, admin, viewer
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="members",
    )
```

**Files to MODIFY:**

`backend/app/models/shop.py`:
```python
from typing import Optional

# Add organization relationship
organization_id: Mapped[Optional[UUID]] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)

organization: Mapped[Optional["Organization"]] = relationship(
    "Organization",
    back_populates="shops",
)
```

---

#### Step 6.2: Backend API - Organization Endpoints

**Files to CREATE:**

`backend/app/routers/organizations.py`:
```python
"""
Organization management API.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.shop import Shop
from app.middleware.shopify_auth import validate_session_token, ShopifySession

logger = get_logger(__name__)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("")
async def list_organizations(
    session_token: Annotated[ShopifySession, Depends(validate_session_token)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """List organizations for current user."""
    # In production, user_id comes from session token
    # For MVP, use shop owner as proxy for user

    # Get shop
    stmt = select(Shop).where(Shop.domain == session_token.shop)
    result = await db_session.execute(stmt)
    shop = result.scalar_one_or_none()

    if not shop:
        return {"organizations": []}

    # If shop has org, return it
    if shop.organization_id:
        org_stmt = select(Organization).where(Organization.id == shop.organization_id)
        org_result = await db_session.execute(org_stmt)
        org = org_result.scalar_one_or_none()

        if org:
            return {
                "organizations": [
                    {
                        "id": str(org.id),
                        "name": org.name,
                        "owner_email": org.owner_email,
                        "shop_count": len(org.shops),
                    }
                ]
            }

    return {"organizations": []}


@router.get("/{org_id}/shops")
async def list_org_shops(
    org_id: UUID,
    session_token: Annotated[ShopifySession, Depends(validate_session_token)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """List shops in an organization."""
    # Verify user has access to org
    # For MVP, just return shops

    stmt = select(Shop).where(Shop.organization_id == org_id)
    result = await db_session.execute(stmt)
    shops = result.scalars().all()

    return {
        "shops": [
            {
                "id": str(shop.id),
                "domain": shop.domain,
                "last_sync_at": shop.last_sync_at.isoformat() if shop.last_sync_at else None,
                "sync_status": shop.sync_status,
            }
            for shop in shops
        ]
    }


@router.post("")
async def create_organization(
    data: dict,
    session_token: Annotated[ShopifySession, Depends(validate_session_token)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Create a new organization."""
    name = data.get("name")

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name required",
        )

    # Get current shop
    stmt = select(Shop).where(Shop.domain == session_token.shop)
    result = await db_session.execute(stmt)
    shop = result.scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found",
        )

    # Create org
    org = Organization(
        name=name,
        owner_email=session_token.user_id or "unknown@example.com",
    )
    db_session.add(org)

    # Add owner as member
    member = OrganizationMember(
        organization_id=org.id,
        email=session_token.user_id or "unknown@example.com",
        role="owner",
    )
    db_session.add(member)

    # Link shop to org
    shop.organization_id = org.id

    await db_session.commit()

    logger.info("Organization created", org_id=str(org.id), name=name)

    return {
        "id": str(org.id),
        "name": org.name,
        "owner_email": org.owner_email,
    }
```

**Files to MODIFY:**

`backend/app/main.py`:
```python
from app.routers import (
    auth_router,
    dashboard_router,
    health_router,
    insights_router,
    organizations_router,  # NEW
    shops_router,
    webhooks_router,
)

app.include_router(organizations_router, prefix="/api")
```

---

#### Step 6.3: Frontend - Store Switcher Component

**Files to CREATE:**

`frontend/app/components/StoreSwitcher.tsx`:
```typescript
import { useState, useEffect } from "react";
import { Select } from "@shopify/polaris";

interface Shop {
  id: string;
  domain: string;
  sync_status: string;
}

export function StoreSwitcher() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [selectedShop, setSelectedShop] = useState<string>("");

  useEffect(() => {
    // Fetch organizations and shops
    fetch("/api/organizations")
      .then(res => res.json())
      .then(data => {
        if (data.organizations && data.organizations.length > 0) {
          const org = data.organizations[0];
          // Fetch shops for org
          fetch(`/api/organizations/${org.id}/shops`)
            .then(res => res.json())
            .then(shopsData => {
              setShops(shopsData.shops || []);
              // Set initial selection from sessionStorage
              const current = sessionStorage.getItem("current_shop_id");
              if (current) {
                setSelectedShop(current);
              } else if (shopsData.shops.length > 0) {
                setSelectedShop(shopsData.shops[0].id);
                sessionStorage.setItem("current_shop_id", shopsData.shops[0].id);
              }
            });
        }
      });
  }, []);

  const handleShopChange = (value: string) => {
    setSelectedShop(value);
    sessionStorage.setItem("current_shop_id", value);
    // Refresh page to reload data for new shop
    window.location.reload();
  };

  if (shops.length <= 1) {
    return null;  // Don't show switcher if only one shop
  }

  const options = shops.map(shop => ({
    label: shop.domain,
    value: shop.id,
  }));

  return (
    <Select
      label="Store"
      labelHidden
      options={options}
      value={selectedShop}
      onChange={handleShopChange}
    />
  );
}
```

**Files to MODIFY:**

`frontend/app/routes/_index.tsx`:
```typescript
import { TitleBar } from "@shopify/app-bridge-react";
import { StoreSwitcher } from "../components/StoreSwitcher";

export default function Dashboard() {
  return (
    <>
      <TitleBar title="Dashboard">
        <StoreSwitcher />
      </TitleBar>
      {/* ... rest of dashboard ... */}
    </>
  );
}
```

**Tests:**
- User with multiple shops sees dropdown
- Switching shops reloads dashboard with new data
- Single-shop users don't see switcher

---

## E) BLOAT REMOVAL PLAN (SAFE AND STAGED)

### **SAFE TO DELETE NOW**

| Item | Files | Risk | Expected Benefit |
|------|-------|------|-----------------|
| Code Analysis Feature | `backend/app/models/code_analysis.py`, `backend/app/routers/code_analysis.py`, `backend/app/services/ai_analyzer.py`, `backend/app/services/ml_intent_classifier.py`, `backend/app/services/deepseek_client.py`, `backend/tests/test_code_analysis.py` | ❌ None (commented out) | -30% LOC, faster builds, cleaner repo |
| Code Analysis Tables | Migration 003: drop `code_submissions`, `analysis_results`, `notification_preferences`, `traffic_metrics` | ❌ None (unused) | Faster DB operations, smaller backups |
| Advanced Analytics Router | `backend/app/routers/analytics.py` | ❌ None (commented out) | Remove confusion about what's active |
| Redis from docker-compose | `docker-compose.yml` lines 23-35 | ❌ None (not used) | Faster local dev startup |

**Action:** Execute Phase 0 steps immediately

---

### **KEEP BUT COMMENT OUT (Feature Flag)**

| Item | Files | Risk | When to Uncomment |
|------|-------|------|-------------------|
| Job Queue Infrastructure | `backend/app/services/job_queue.py` | ⚠️ Low (might need for scheduled sync) | When implementing background jobs (scheduled daily sync, batch insight computation) |
| Notification Service | `backend/app/services/notification_service.py` | ⚠️ Low (might need for alerts) | When implementing email notifications (critical insights, sync failures) |
| AI Provider Config | `backend/app/core/config.py` lines 68-76 | ❌ None (unused) | When implementing AI-powered insights (sentiment, predictions) |

**Action:** Add `# FUTURE USE:` header with comment explaining when to uncomment

---

### **POSTPONE (Evaluate Later)**

| Item | Files | Risk | Decision Criteria |
|------|-------|------|-------------------|
| Repository Pattern Abstraction | `backend/app/repositories/` | ⚠️ Medium (breaks architecture) | Keep for testability. Only remove if tests become impossible to maintain |
| Demo Mode Fallback | All routes returning demo data | ⚠️ Low (helpful for dev) | Remove only if it masks production errors. Keep but limit to `DEBUG=True` |

**Action:** Keep as-is for now, re-evaluate in 3 months

---

## F) DOCUMENTATION DELIVERABLES (PARALLEL)

### **Documentation to CREATE (with Timing)**

| Document | When to Write | Owner | Purpose |
|----------|--------------|-------|---------|
| `ONBOARDING_MERCHANT_GUIDE.md` | Phase 2 (OAuth complete) | Engineering | Step-by-step for merchants installing app |
| `PERMISSION_MATRIX.md` | Phase 2 (OAuth complete) | Engineering | Scope justification for Shopify app review |
| `ARCHITECTURE.md` | Phase 3 (Sync complete) | Engineering | System architecture, data flow diagrams |
| `MULTI_ORG_GUIDE.md` | Phase 6 (Multi-org complete) | Engineering | How to use organizations, invite team |
| `DATA_SYNC_WEBHOOKS.md` | Phase 4 (Webhooks complete) | Engineering | Sync strategy, webhook handling, troubleshooting |
| `API_REFERENCE.md` | Continuous | Engineering | API endpoint documentation (auto-generated from OpenAPI) |

---

### **Documentation to UPDATE**

| Document | Changes | When |
|----------|---------|------|
| `README.md` | Replace "EcomDash V2" with "Growzilla-Beta", update quick start to use Shopify CLI | Phase 1 |
| `FORENSIC_CODEBASE_ANALYSIS.md` | Mark as "PRE-REFACTOR ARCHIVE" | Phase 0 |
| `docker-compose.yml` | Add comments explaining future services (Redis, worker) | Phase 0 |
| `.env.example` | Add Shopify credentials, App Bridge API key | Phase 1 |

---

### **Template: ONBOARDING_MERCHANT_GUIDE.md**

```markdown
# Growzilla-Beta Merchant Onboarding Guide

## Installation (2 minutes)

1. **Click Install Link**
   ```
   https://admin.shopify.com/oauth/install?client_id=YOUR_API_KEY
   ```

2. **Review Permissions**
   - ✅ Read products (for inventory insights)
   - ✅ Read orders (for revenue analytics)
   - ❌ No write access (we can't modify your store)

3. **Click "Install app"**

4. **You're done!** Growzilla appears in your Shopify Admin sidebar.

## What Happens Next

- **Initial Sync:** 5-15 minutes for first data sync
- **Dashboard:** View revenue stats, top products, AI insights
- **Insights:** Generated within 24 hours of first sync

## Multi-Store Setup (Agencies)

1. **Create Organization**
   - Settings → Organizations → Create New
   - Name your agency/company

2. **Install on Additional Stores**
   - Repeat installation for each store
   - All stores automatically linked to your org

3. **Switch Between Stores**
   - Use store dropdown in dashboard header
   - Data filtered to selected store

## Uninstall

Shopify Admin → Settings → Apps → Growzilla → Delete

All your data is automatically deleted (GDPR compliant).

## Need Help?

Email: support@growzilla.xyz
```

---

### **Template: PERMISSION_MATRIX.md**

```markdown
# Shopify Permission Matrix - Growzilla-Beta

## Scopes Requested

| Scope | Required? | Justification | Data Accessed | User Benefit |
|-------|-----------|--------------|---------------|--------------|
| `read_products` | ✅ YES | Analyze inventory levels for stockout alerts | Product title, handle, inventory quantity, price | Prevent lost sales from stockouts |
| `read_orders` | ✅ YES | Compute revenue trends, AOV, identify high performers | Order total, line items, processed date | Data-driven revenue optimization |

## Scopes NOT Requested (Minimal Principle)

| Scope | Why Not Needed | Alternative |
|-------|----------------|-------------|
| `read_customers` | Customer analysis not in MVP | Can be added in Phase 2 if needed |
| `read_analytics` | Traffic data not in MVP | Can be added when traffic insights implemented |
| `write_*` | Read-only app, no store modifications | N/A |

## Data Retention

- **Products:** Cached for 24 hours, refreshed via webhook
- **Orders:** Last 90 days synced, older data pruned monthly
- **On Uninstall:** All data deleted within 24 hours (GDPR)

## For Shopify App Review

This app provides business intelligence by analyzing product and order data. We help merchants:
- Identify stockout risks before they happen
- Optimize inventory allocation
- Discover revenue opportunities

All data access is read-only. We do not modify the merchant's store in any way.
```

---

## G) ROLLBACK & SAFETY STRATEGY

### **Per-Phase Rollback Plan**

| Phase | Rollback Strategy | Safety Mechanism |
|-------|------------------|------------------|
| Phase 0 (Bloat Removal) | Git revert, restore deleted files | Feature still commented out in main.py, safe |
| Phase 1 (App Bridge) | Remove App Bridge imports, revert to standalone | Feature flag: `ENABLE_APP_BRIDGE=false` in .env |
| Phase 2 (OAuth) | Keep existing shop creation, disable OAuth routes | OAuth routes optional, manual shop creation still works |
| Phase 3 (Sync) | Sync fails gracefully, returns error | Background task failure doesn't crash API |
| Phase 4 (Webhooks) | Invalid HMAC returns 401, doesn't crash | Webhook failures logged but don't affect app |
| Phase 5 (Dashboard) | Dashboard works with or without App Bridge | Degraded mode: standalone dashboard |
| Phase 6 (Multi-Org) | organization_id nullable, single-shop mode works | Backward compatible: NULL org_id = standalone shop |

### **Feature Flags (Environment Variables)**

Add to `backend/app/core/config.py`:
```python
# Feature flags
enable_app_bridge: bool = True  # Disable to run as standalone
enable_webhooks: bool = True  # Disable webhook handling
enable_multi_org: bool = True  # Disable org features
enable_auto_sync: bool = False  # FUTURE: Enable scheduled background sync
```

---

## H) UNKNOWNS & RESOLUTION STRATEGY

### **Critical Unknowns**

1. **Missing auth-proxy service**
   - **Evidence:** `backend/app/routers/shops.py:42` mentions auth-proxy
   - **Resolution:** Implement OAuth in FastAPI backend (Phase 2) instead of external service
   - **Alternative:** If auth-proxy exists externally, document its API contract

2. **Shopify App credentials**
   - **Evidence:** Hardcoded in growzilla-beta onboarding
   - **Resolution:** Use existing credentials: `client_id=02e4e67112ab0bf60bbd4de3afbff59e`
   - **Verify:** Check Shopify Partner Dashboard for app details

3. **App handle for redirect URL**
   - **Evidence:** Not found in config
   - **Resolution:** Check Partner Dashboard, likely `growzilla-beta`
   - **Temporary:** Use `shopify_app_handle="growzilla-beta"` in config

4. **Production deployment URL**
   - **Evidence:** `growzilla-app.onrender.com` in onboarding guide
   - **Resolution:** Use same URL for OAuth callback
   - **Verify:** Ensure Render deployment matches

---

## EXECUTION SUMMARY

### **Total Duration:** ~14 days (2.5 weeks)

- Phase 0: 2 days (bloat removal)
- Phase 1: 3 days (App Bridge)
- Phase 2: 2 days (OAuth)
- Phase 3: 3 days (sync)
- Phase 4: 2 days (webhooks)
- Phase 5: 1 day (dashboard wrap)
- Phase 6: 3 days (multi-org)

### **Team Structure**

- **1 Staff Engineer:** Phases 0-2 (foundation)
- **1 Backend Engineer:** Phases 3-4 (sync + webhooks)
- **1 Frontend Engineer:** Phases 1, 5 (App Bridge + dashboard)
- **1 Full-Stack Engineer:** Phase 6 (multi-org)

### **Success Criteria**

1. Merchant can install app via OAuth link
2. App loads embedded in Shopify Admin
3. Dashboard shows real products/orders from GraphQL
4. Webhooks keep data fresh (< 30 sec latency)
5. Agency can manage 10+ stores in one org
6. Shopify public app submission approved (minimal scopes)

### **Risk Mitigation**

- Incremental phases allow early feedback
- Backward compatibility (nullable org_id, feature flags)
- Comprehensive rollback strategy per phase
- Demo mode fallback for dev/testing

---

**PLAN COMPLETE. READY FOR EXECUTION.**

*Do NOT implement until explicitly instructed. This is planning output only.*
