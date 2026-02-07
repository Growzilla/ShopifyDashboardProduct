# FORENSIC CODEBASE ANALYSIS
## Shopify Embedded Admin App - EcomDash V2

**Analysis Date:** 2026-02-04
**Codebase:** EcomDashQ1BetaCohort
**Status:** Production-ready MVP with significant bloat
**Total Backend LOC:** ~6,773 lines Python

---

## 1. SYSTEM MAP (Evidence-Based)

### 1.1 RUNTIME COMPONENTS

#### **A. FRONTEND (React Router 7 + Polaris)**

**Entrypoint:**
- `frontend/app/root.tsx` - App initialization with QueryClient + Polaris AppProvider

**Key Modules:**
```
frontend/app/
├── root.tsx                     # Main app wrapper, QueryClient setup, ErrorBoundary
├── routes/
│   ├── _index.tsx              # Dashboard page (stats + revenue chart + ONE insight)
│   └── analytics.dashboard.tsx # Secondary analytics route
├── components/
│   ├── StatsCard.tsx           # Metric display cards (Revenue, Orders, AOV)
│   ├── RevenueChart.tsx        # Time-series chart visualization
│   └── InsightsList.tsx        # AI insight display component
├── services/
│   └── api.ts                  # TanStack Query hooks for backend API
├── utils/
│   └── format.ts               # Number/currency formatting
└── styles/
    └── global.css              # Polaris + custom styles
```

**What it does:**
- Displays analytics dashboard with Polaris UI
- Uses TanStack Query for data fetching with SSR-safe initialization
- Implements demo mode fallback (hardcoded DEMO_SHOP_UUID: `00000000-0000-0000-0000-000000000001`)
- No App Bridge integration detected - missing Shopify embedded app setup
- No OAuth flow in frontend - delegates to external auth-proxy

**Shopify Integration:**
- ❌ **NO App Bridge SDK** - Not a true embedded app
- ❌ **NO Session Token handling** - Missing authentication
- ❌ **NO Shopify navigation** - Uses standard React Router
- ✅ Uses Polaris components correctly (semantic tokens, Badge tones)

---

#### **B. BACKEND (FastAPI + SQLAlchemy 2.0)**

**Entrypoint:**
- `backend/app/main.py` - FastAPI application factory with lifespan management

**Core Architecture:**
```
backend/app/
├── main.py                     # App factory, middleware registration, router mounting
├── core/
│   ├── config.py               # Pydantic Settings (DB, Redis, Shopify, AI providers)
│   ├── database.py             # AsyncEngine, sessionmaker, Base model
│   ├── security.py             # Fernet encryption, JWT, HMAC verification
│   └── logging.py              # Structured logging (structlog)
├── models/                     # SQLAlchemy ORM models
│   ├── shop.py                 # Shop (tenant key: domain, encrypted access_token)
│   ├── product.py              # Product (synced from Shopify)
│   ├── order.py                # Order (synced from Shopify, JSONB line_items)
│   ├── insight.py              # AI-generated business insights
│   ├── code_analysis.py        # BLOAT: Code submission/analysis feature
│   └── analytics.py            # BLOAT: Advanced analytics models
├── routers/                    # API endpoints
│   ├── health.py               # /health, /health/ready
│   ├── shops.py                # /api/shops (CRUD, sync trigger)
│   ├── insights.py             # /api/insights (list, dismiss, action)
│   ├── dashboard.py            # /api/dashboard/stats, revenue-chart, summary
│   ├── code_analysis.py        # BLOAT: Commented out in main.py
│   └── analytics.py            # BLOAT: Commented out in main.py
├── services/
│   ├── shopify_client.py       # GraphQL API client (rate limit handling, retries)
│   ├── insights_engine.py      # 5 insight algorithms (understocked, overstock, coupons)
│   ├── ai_analyzer.py          # BLOAT: DeepSeek/OpenAI integration
│   ├── analytics_service.py    # BLOAT: Pattern analysis
│   ├── notification_service.py # Email notifications via Resend
│   ├── job_queue.py            # BLOAT: ARQ background jobs
│   └── deepseek_client.py      # BLOAT: AI model client
├── repositories/               # Data access layer
│   ├── base.py                 # Generic CRUD operations
│   ├── shop.py                 # Shop-specific queries
│   └── insight.py              # Insight-specific queries
├── schemas/                    # Pydantic request/response models
│   ├── shop.py                 # ShopCreate, ShopResponse, ShopUpdate, ShopSyncRequest
│   ├── insight.py              # InsightResponse, PaginatedInsightsResponse
│   └── dashboard.py            # DashboardStats, RevenueChartData, TopProduct
└── middleware/
    ├── request_id.py           # X-Request-ID injection
    └── error_handler.py        # Global exception handling
```

**What it does:**
- REST API for analytics dashboard
- Stores shops, products, orders, insights in PostgreSQL
- Encrypts Shopify access tokens (Fernet symmetric encryption)
- Computes AI insights from order/product data
- Demo mode fallback for development (returns hardcoded data if shop not found)

**Shopify Integration:**
- ✅ GraphQL Admin API client (`shopify_client.py`)
- ✅ Rate limit handling (2 calls/sec, exponential backoff)
- ✅ Token encryption/decryption
- ✅ HMAC webhook verification implemented (`security.py:89-104`)
- ❌ **NO webhook routes registered** - verification exists but no handlers
- ❌ **NO OAuth flow** - delegates to external "auth-proxy" (not found in repo)
- ❌ **NO session storage** - JWT-based but no Shopify session persistence

---

#### **C. DATA LAYER (PostgreSQL + SQLAlchemy)**

**Migrations:** `backend/alembic/versions/`
- `001_initial_schema.py` - Shops, Products, Orders, Insights, Code Submissions, Notifications
- `002_analytics_schema.py` - Advanced analytics tables

**Tenancy Key:** `shop.domain` (unique index)

**Data Models:**

| Table | Tenant FK | Purpose | Key Fields |
|-------|-----------|---------|------------|
| `shops` | - | Root tenant entity | `domain` (unique), `access_token_encrypted`, `scopes` |
| `products` | `shop_id` | Shopify product mirror | `shopify_id`, `title`, `total_inventory` |
| `orders` | `shop_id` | Shopify order mirror | `shopify_id`, `total_price`, `line_items` (JSONB) |
| `insights` | `shop_id` | AI-generated insights | `type`, `severity`, `dismissed_at` |
| `code_submissions` | `shop_id` | BLOAT: Code analysis | `status`, `analyzed_at` |
| `analysis_results` | `submission_id` | BLOAT: AI code review | `bugs`, `security_issues` |

**Critical Observations:**
- ✅ All child tables have ON DELETE CASCADE (GDPR compliance)
- ✅ Unique constraints: `(shop_id, shopify_id)` for products/orders (prevent duplicates)
- ✅ Indexes on `shop_id`, `processed_at`, `created_at`, `severity`, `type`
- ❌ **NO org_id or multi-store grouping** - one shop = one tenant
- ❌ **NO sync metadata** - no last_synced_cursor, no incremental sync tracking
- ❌ Orders store line_items as JSONB blob - no normalized line_items table

---

#### **D. JOBS/QUEUES/CRONS**

**Found in code but NOT ACTIVE:**
- `backend/app/services/job_queue.py` - ARQ (Redis-based job queue) implementation
- Defines cron jobs for pattern analysis, traffic metrics, adaptive scheduling
- **STATUS:** Commented out in main.py, no worker process in docker-compose.yml

**Evidence:**
```python
# From main.py:17-23
# COMMENTED OUT FOR MVP - Overengineered features:
# app.include_router(code_analysis_router, prefix="/api")
# app.include_router(analytics_router)
```

**Sync Mechanism:**
- `backend/app/routers/shops.py:111-144` - `/shops/{shop_id}/sync` endpoint
- Triggers `sync_shop_data()` via FastAPI BackgroundTasks
- **CRITICAL:** `sync_shop_data` function NOT FOUND in codebase (broken reference)

---

#### **E. INTEGRATIONS**

**Shopify GraphQL Client:**
- **File:** `backend/app/services/shopify_client.py`
- **API Version:** 2024-01 (hardcoded, should be configurable)
- **Features:**
  - ✅ Token decryption on init
  - ✅ Rate limit handling (429 retry with exponential backoff)
  - ✅ Error handling + logging
  - ✅ Pagination support (cursor-based)
  - ❌ No bulk operations
  - ❌ No GraphQL cost calculation
  - ❌ No query batching

**Queries Implemented:**
1. `get_shop_info()` - Basic shop metadata
2. `get_products(first, after)` - Products with pagination
3. `get_orders(first, after, query)` - Orders with line items

**Missing Queries:**
- No inventory level fetching
- No customer data queries
- No checkout/cart queries (for abandonment insights)
- No analytics API queries (for traffic data)

**AI Provider Integration (BLOAT):**
- DeepSeek via OpenRouter (`backend/app/services/deepseek_client.py`)
- OpenAI fallback (`backend/app/core/config.py:68-70`)
- ML Intent Classifier (`backend/app/services/ml_intent_classifier.py`)
- **STATUS:** Used only for code analysis feature (commented out)

**Notification Service:**
- Resend API for email (`backend/app/services/notification_service.py`)
- **STATUS:** Configured but unused

---

### 1.2 REFERENCE IMPLEMENTATIONS

**retail-os/** - Complete Shopify embedded app (not the main project)
- Uses `@shopify/shopify-app-react-router` correctly
- Implements OAuth flow (`app/routes/auth.$.tsx`)
- Webhook handlers for:
  - `webhooks.app.uninstalled.tsx`
  - `webhooks.app.scopes_update.tsx`
  - `webhooks.orders.create.tsx`
  - `webhooks.orders.updated.tsx`
  - `webhooks.products.update.tsx`
  - `webhooks.inventory.update.tsx`
- Prisma session storage
- **KEY INSIGHT:** This is a reference implementation showing correct patterns

**growzilla-beta/** - Marketing site (Next.js)
- No relevance to Shopify integration
- Design system documentation (`GROWZILLA_DESIGN_PATTERNS.md`)

---

## 2. SOLVED PROBLEMS (Keep/Adjust/Risky)

### ✅ KEEP AS-IS (Strong Wins)

1. **Token Encryption** - `backend/app/core/security.py:29-44`
   - Uses Fernet symmetric encryption (FIPS-compliant)
   - Derives key from env variable via SHA256
   - Status: **Keep as-is** ✅

2. **Shop Tenancy Model** - `backend/app/models/shop.py`
   - Domain as unique identifier
   - Encrypted access token storage
   - Cascade delete for GDPR compliance
   - Status: **Keep as-is** ✅

3. **GraphQL Client Architecture** - `backend/app/services/shopify_client.py`
   - Rate limit handling (exponential backoff)
   - Automatic retries (3 attempts)
   - Proper error logging
   - Status: **Keep as-is** ✅

4. **Repository Pattern** - `backend/app/repositories/`
   - Clean separation of data access logic
   - Generic CRUD operations in base class
   - Async/await properly implemented
   - Status: **Keep as-is** ✅

5. **Structured Logging** - `backend/app/core/logging.py`
   - Uses structlog for JSON output
   - Request ID propagation
   - Status: **Keep as-is** ✅

6. **Demo Mode Fallback** - Throughout frontend + backend
   - Hardcoded demo data for development
   - Graceful degradation when DB unavailable
   - Status: **Keep as-is** ✅ (helpful for dev/testing)

7. **Polaris UI Implementation** - `frontend/app/`
   - Correct use of semantic tokens (no hardcoded colors)
   - Badge severity tones
   - SSR-safe React Query setup
   - Status: **Keep as-is** ✅

### ⚠️ NEEDS SMALL FIX

8. **HMAC Webhook Verification** - `backend/app/core/security.py:89-104`
   - Verification logic exists
   - Status: **Needs webhook routes** ⚠️
   - Risk: Medium (webhooks won't work without routes)

9. **Sync Trigger Endpoint** - `backend/app/routers/shops.py:111-144`
   - References `sync_shop_data` function
   - Status: **Broken reference** ⚠️
   - Risk: High (sync will crash at runtime)
   - Fix: Implement `backend/app/services/data_sync.py`

10. **Shopify API Version** - `backend/app/services/shopify_client.py:27`
    - Hardcoded to `2024-01`
    - Status: **Should be configurable** ⚠️
    - Risk: Low (works but inflexible)

### 🔴 RISKY (Use with Caution)

11. **No Multi-Store Support** - `backend/app/models/`
    - One shop = one tenant (no org/company grouping)
    - Status: **Architecture limitation** 🔴
    - Risk: High for enterprise customers
    - Cannot support agency/multi-store use cases

12. **JSONB Line Items Storage** - `backend/app/models/order.py`
    - Stores line items as unstructured JSON
    - Status: **Query performance risk** 🔴
    - Risk: Medium (can't efficiently filter/aggregate by product)
    - Workaround: In-memory aggregation (current approach)

13. **No Incremental Sync** - Missing sync cursor tracking
    - No `last_synced_cursor` field
    - Status: **Full sync every time** 🔴
    - Risk: High at scale (rate limit exhaustion, slow syncs)

---

## 3. BLOAT & OVERENGINEERING

### 🗑️ CATEGORY A: COMPLETELY UNUSED (Safe to Delete)

1. **Code Analysis Feature** - `backend/app/models/code_analysis.py`, `backend/app/routers/code_analysis.py`, `backend/app/services/ai_analyzer.py`
   - **Evidence:** Commented out in `main.py:17,103`
   - **Tables:** `code_submissions`, `analysis_results`, `notification_preferences`
   - **Risk of Removal:** ❌ None (already disabled)
   - **Recommendation:** **DELETE** - Remove models, migrations, routers, services
   - **Files to Delete:**
     - `backend/app/models/code_analysis.py`
     - `backend/app/routers/code_analysis.py`
     - `backend/app/services/ai_analyzer.py`
     - `backend/app/services/ml_intent_classifier.py`
     - `backend/tests/test_code_analysis.py`
   - **Migration:** Create rollback migration to drop tables

2. **Advanced Analytics Router** - `backend/app/routers/analytics.py`
   - **Evidence:** Commented out in `main.py:23,104`
   - **Risk of Removal:** ❌ None (already disabled)
   - **Recommendation:** **DELETE** if not needed for roadmap

3. **Job Queue Infrastructure** - `backend/app/services/job_queue.py`
   - **Evidence:** No worker process in `docker-compose.yml`, no imports
   - **Code:** 400+ lines of ARQ cron job scheduling
   - **Risk of Removal:** ⚠️ Low (might be needed for future background jobs)
   - **Recommendation:** **COMMENT OUT** until background jobs are needed
   - Keep file but add `# FUTURE: Uncomment when implementing background sync`

4. **DeepSeek AI Client** - `backend/app/services/deepseek_client.py`
   - **Evidence:** Only used by deleted code analysis feature
   - **Risk of Removal:** ❌ None
   - **Recommendation:** **DELETE** (or move to separate repo if valuable)

5. **Analytics Models** - `backend/app/models/analytics.py`
   - **Evidence:** Advanced metrics tracking not used in MVP
   - **Risk of Removal:** ⚠️ Medium (depends on roadmap)
   - **Recommendation:** **FEATURE FLAG** - Keep code, disable via config

### 🚧 CATEGORY B: OVERENGINEERED (Simplify)

6. **Triple AI Provider Fallback** - `backend/app/core/config.py:68-76`
   - OpenAI + OpenRouter + DeepSeek config
   - **Evidence:** Insights engine uses zero AI (pure SQL analytics)
   - **Risk:** Misleading complexity
   - **Recommendation:** **COMMENT OUT** - Keep for future AI features, mark as "not yet used"

7. **Notification Service** - `backend/app/services/notification_service.py`
   - Resend API integration
   - **Evidence:** No callers in codebase
   - **Risk of Removal:** ⚠️ Low (might be needed for alerts)
   - **Recommendation:** **COMMENT OUT** until email alerts are built

8. **Traffic Metrics Table** - `backend/alembic/versions/001_initial_schema.py:154-165`
   - Hourly request tracking
   - **Evidence:** No writes to this table in codebase
   - **Risk of Removal:** ❌ None (dead table)
   - **Recommendation:** **DROP TABLE** in next migration

### 📊 CATEGORY C: PREMATURE OPTIMIZATION (Monitor)

9. **Redis Caching** - `backend/app/core/config.py:39-40`
   - Configured but not used
   - **Evidence:** No Redis operations in codebase, only in docker-compose
   - **Risk:** Wasted infrastructure cost
   - **Recommendation:** **REMOVE from docker-compose** until caching is implemented

10. **Repository Abstraction Layer**
    - Adds indirection for simple CRUD
    - **Evidence:** Only 3 repositories, most are simple pass-throughs
    - **Risk of Removal:** ⚠️ Medium (breaks architecture)
    - **Recommendation:** **KEEP for now** - Helps with testability

---

## 4. DATA FLOW TRACE (As-Is)

### 4.1 DATA FLOW PATHWAYS

```
┌─────────────────────────────────────────────────────────────────┐
│                     SHOPIFY STORE                               │
│  (products, orders, customers, inventory)                       │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  │ ❌ NO AUTOMATED SYNC
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  MANUAL SYNC TRIGGER (POST /api/shops/{id}/sync)               │
│  - Triggered by user or external scheduler                      │
│  - Calls sync_shop_data() via BackgroundTasks                   │
│  - ❌ BROKEN: sync_shop_data NOT FOUND IN CODEBASE              │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  │ (intended flow - not implemented)
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  SHOPIFY GRAPHQL CLIENT (shopify_client.py)                     │
│  - Fetches products: get_products(first=50, after=cursor)       │
│  - Fetches orders: get_orders(first=50, after=cursor)           │
│  - Rate limited: 2 calls/sec, exponential backoff               │
│  - ✅ Pagination support                                         │
│  - ❌ No bulk operations                                         │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  POSTGRESQL DATABASE (AsyncSession)                             │
│  - Upsert products (shop_id + shopify_id unique constraint)     │
│  - Upsert orders (shop_id + shopify_id unique constraint)       │
│  - JSONB line_items storage (no normalization)                  │
│  - ❌ No sync cursor tracking (full sync every time)            │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  INSIGHTS ENGINE (insights_engine.py)                           │
│  - Runs SQL aggregations on orders/products                     │
│  - Computes 5 insight types:                                    │
│    1. Understocked Winners (inventory < 7 days)                 │
│    2. Overstock Slow Movers (P80 inventory, P20 sales)          │
│    3. Coupon Cannibalization (discount rate > 40%)              │
│    4. Traffic-Sales Mismatch (NOT IMPLEMENTED)                  │
│    5. Checkout Drop-off (NOT IMPLEMENTED)                       │
│  - ❌ No AI - pure SQL analytics                                │
│  - ❌ No incremental computation                                │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  DASHBOARD API (/api/dashboard/*)                               │
│  - GET /stats - Revenue, Orders, AOV (yesterday vs 7-day avg)   │
│  - GET /revenue-chart - Daily aggregates (7d/30d/90d)           │
│  - GET /insights - Paginated insights (demo fallback)           │
│  - ✅ Demo mode if shop not found                               │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (React Router 7 + TanStack Query)                     │
│  - Fetches via /api/* endpoints                                 │
│  - SSR-safe QueryClient                                         │
│  - Demo shop UUID fallback (sessionStorage)                     │
│  - ❌ No App Bridge - not embedded                              │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 TENANCY IDENTIFICATION

**Current Approach:**
- `shop.domain` (string) - mystore.myshopify.com
- Unique index on domain
- All queries filter by `shop_id` (UUID FK)

**Multi-Store Breaks When:**
1. Agency wants to manage 50 stores under one account → ❌ No org_id grouping
2. User switches between stores → ❌ No store-switching UI
3. Billing by org not store → ❌ No org-level aggregation
4. Permissions (admin vs viewer) → ❌ No RBAC

**What's Missing for Orgs/Many Stores:**
- `organizations` table (org_id, name, owner)
- `organization_members` table (org_id, user_id, role)
- `shops.organization_id` FK (nullable for backward compat)
- Store switcher UI component
- Org-level billing aggregation

---

### 4.3 TOP 10 DATA CORRECTNESS RISKS

#### **🔴 CRITICAL (P0)**

1. **Broken Sync Implementation**
   - **Where:** `backend/app/routers/shops.py:130`
   - **Issue:** `from app.services.data_sync import sync_shop_data` - module does not exist
   - **Impact:** Sync endpoint crashes at runtime, no data ingestion possible
   - **Evidence:** `grep -r "sync_shop_data" backend/` returns only the import
   - **Fix Required:** Implement `backend/app/services/data_sync.py` with pagination

2. **No Webhook Handlers**
   - **Where:** Missing `backend/app/routers/webhooks.py`
   - **Issue:** HMAC verification exists but no routes to receive webhooks
   - **Impact:** Can't react to Shopify events (uninstalls, order updates, product changes)
   - **Data Staleness:** Orders/products become stale without webhook updates
   - **Evidence:** No webhook registration in main.py, no webhook routes
   - **Fix Required:** Create webhook router with handlers for:
     - `app/uninstalled` (GDPR deletion)
     - `orders/create`, `orders/updated`
     - `products/create`, `products/update`, `products/delete`
     - `inventory_levels/update`

3. **No OAuth Flow**
   - **Where:** Missing auth routes in backend
   - **Issue:** Comments reference "auth-proxy" but it doesn't exist in repo
   - **Impact:** Cannot onboard new stores, hardcoded demo shop only
   - **Evidence:** No `/auth/callback` route, no Shopify app installation flow
   - **Fix Required:** Implement OAuth callback handler or document external auth-proxy

4. **Full Sync Every Time (No Incremental Sync)**
   - **Where:** Missing sync cursor tracking in `shops` table
   - **Issue:** No `last_products_cursor`, `last_orders_cursor` fields
   - **Impact:**
     - Fetches all products/orders every sync (rate limit exhaustion)
     - Slow sync for stores with 10k+ products
     - Wasted API calls
   - **Evidence:** GraphQL client has pagination but no cursor persistence
   - **Fix Required:** Add cursor fields to `shops`, implement incremental sync logic

#### **🟠 HIGH (P1)**

5. **Multi-Tenant Isolation Not Enforced**
   - **Where:** Missing shop_id validation in repositories
   - **Issue:** If shop_id parameter is manipulated, could access other tenants' data
   - **Impact:** Data leakage between stores
   - **Evidence:** No middleware to validate shop_id against authenticated session
   - **Fix Required:** Add shop ownership validation middleware

6. **JSONB Line Items Can't Be Queried Efficiently**
   - **Where:** `backend/app/models/order.py` - `line_items` JSONB column
   - **Issue:** Insights engine must load all orders into memory to aggregate by product
   - **Impact:**
     - Memory exhaustion for stores with 100k+ orders
     - Slow insight computation (no indexes on JSONB)
   - **Evidence:** `insights_engine.py` uses Python loops not SQL aggregation
   - **Fix Required:** Create `order_line_items` normalized table

7. **No Idempotency for Webhooks**
   - **Where:** No `webhook_events` table
   - **Issue:** If webhook is retried by Shopify, could create duplicate insights/data
   - **Impact:** Duplicate data, incorrect analytics
   - **Evidence:** No deduplication logic in codebase
   - **Fix Required:** Store processed webhook IDs, check before processing

8. **No Sync Error Handling**
   - **Where:** Missing error recovery in (unimplemented) sync logic
   - **Issue:** If sync fails mid-way (rate limit, network error), partial data with no rollback
   - **Impact:** Inconsistent state, missing orders/products
   - **Evidence:** No transaction boundaries around sync operations
   - **Fix Required:** Wrap sync in DB transaction, implement retry logic

#### **🟡 MEDIUM (P2)**

9. **Demo Mode Masks Production Issues**
   - **Where:** All routes return demo data if shop not found
   - **Issue:** Production errors might return fake data instead of 404
   - **Impact:** User sees stale demo data instead of real error
   - **Evidence:** `dashboard.py:86-96`, `insights.py:92-102`
   - **Fix Required:** Only enable demo mode when `DEBUG=True` in config

10. **No Sync Status Visibility**
    - **Where:** `shops.sync_status` field exists but never updated correctly
    - **Issue:** Users can't tell if sync is running, succeeded, or failed
    - **Impact:** No observability, can't debug sync issues
    - **Evidence:** `sync_status` set to "syncing" but never set to "completed"/"failed"
    - **Fix Required:** Update sync_status in sync flow, expose in API

---

## 5. MUST-NOT-BREAK INVARIANTS

### 🛡️ SECURITY INVARIANTS

1. **Access Token Encryption**
   - **Invariant:** All Shopify access tokens MUST be encrypted at rest
   - **Location:** `backend/app/core/security.py:33-35`, `backend/app/routers/shops.py:45`
   - **Verification:** Never store plaintext access_token in database
   - **Test:** Inspect `shops.access_token_encrypted` column - must be Fernet-encrypted

2. **Webhook HMAC Verification**
   - **Invariant:** All Shopify webhooks MUST verify HMAC signature
   - **Location:** `backend/app/core/security.py:89-104`
   - **Verification:** Reject webhooks with invalid/missing HMAC
   - **Test:** Send webhook without HMAC → must return 401

3. **Tenant Isolation**
   - **Invariant:** Users can ONLY access data for shops they own
   - **Location:** All queries MUST filter by `shop_id`
   - **Verification:** No cross-tenant data leakage
   - **Test:** Query with wrong shop_id → must return 404 not 403 (info leak)

### 🔐 DATA INTEGRITY INVARIANTS

4. **Shopify ID Uniqueness**
   - **Invariant:** `(shop_id, shopify_id)` MUST be unique for products/orders
   - **Location:** `backend/alembic/versions/001_initial_schema.py:57,79`
   - **Verification:** Prevent duplicate syncs from creating duplicate records
   - **Test:** Insert same product twice → second insert should UPDATE not INSERT

5. **Cascade Deletion (GDPR)**
   - **Invariant:** Deleting a shop MUST delete all related data
   - **Location:** All FKs have `ondelete='CASCADE'`
   - **Verification:** Comply with GDPR "right to be forgotten"
   - **Test:** Delete shop → verify products, orders, insights also deleted

6. **Sync Atomicity**
   - **Invariant:** Sync operations MUST be atomic (all-or-nothing)
   - **Location:** NOT YET ENFORCED (sync implementation missing)
   - **Verification:** Partial sync should rollback on error
   - **Test:** Kill sync mid-way → database should be unchanged OR fully updated

### ⚙️ OPERATIONAL INVARIANTS

7. **Rate Limit Compliance**
   - **Invariant:** Shopify API calls MUST respect 2 req/sec limit
   - **Location:** `backend/app/services/shopify_client.py:29`
   - **Verification:** Exponential backoff on 429 errors
   - **Test:** Monitor Shopify API call rate, ensure < 2/sec

8. **Structured Logging**
   - **Invariant:** All errors MUST be logged with context (shop_id, request_id)
   - **Location:** `backend/app/core/logging.py`, all services
   - **Verification:** Errors are traceable to specific shop/request
   - **Test:** Grep logs for shop_id, request_id in error entries

9. **Health Check Accuracy**
   - **Invariant:** `/health/ready` MUST fail if database unavailable
   - **Location:** `backend/app/routers/health.py`
   - **Verification:** Kubernetes should not route to unhealthy pods
   - **Test:** Stop Postgres → health check returns 503

---

## 6. QUESTIONS THE CODEBASE DOES NOT ANSWER

### 🤷 ARCHITECTURE UNKNOWNS

1. **Where is the OAuth flow?**
   - Code references "auth-proxy" but it's not in the repo
   - Is it a separate service? Hosted where? Code in another repo?
   - How do shops get onboarded?

2. **How is shop_id passed to the frontend?**
   - Frontend uses `sessionStorage.getItem("shop_id")` but who sets it?
   - No App Bridge session token handling
   - Missing authentication middleware

3. **Is this an embedded app or standalone web app?**
   - Polaris UI suggests embedded app
   - No App Bridge SDK usage → standalone?
   - No `shopify.app.toml` in main project (exists in retail-os reference)

4. **What triggers sync?**
   - POST /api/shops/{id}/sync exists but who calls it?
   - Is there a cron job? External scheduler? User button?
   - No scheduled jobs in docker-compose

5. **How are webhooks registered?**
   - HMAC verification exists but no webhook routes
   - Is there a setup script that registers webhooks with Shopify?
   - Missing `shopify.registerWebhooks()` call

### 📊 DATA & BUSINESS LOGIC UNKNOWNS

6. **What data is actually needed from Shopify?**
   - Insights require orders + products
   - Are customers, inventory levels, traffic needed?
   - Missing requirements doc

7. **How often should sync run?**
   - Real-time webhooks? Hourly batch? Daily?
   - No performance requirements documented

8. **What's the target scale?**
   - How many shops? Orders per shop? Products per shop?
   - Current design assumes < 10k orders (loads all into memory)

9. **Are there any external dependencies?**
   - References to "auth-proxy" suggest external auth service
   - Any other microservices? Message queues? CDN?

10. **What's the deployment model?**
    - Docker Compose is for local dev
    - `render.yaml` exists → Render.com deployment?
    - Multi-region? Single-tenant or multi-tenant SaaS?

### 🔒 SECURITY & COMPLIANCE UNKNOWNS

11. **How is RBAC handled?**
    - No user/role tables
    - Is there a separate auth service?
    - How do you differentiate admin vs viewer?

12. **How is billing tracked?**
    - No subscription or usage tracking tables
    - Shopify App Store billing? Stripe? Manual?

13. **Are there any compliance requirements?**
    - GDPR deletion implemented (cascade delete)
    - What about CCPA, SOC 2, PCI-DSS?
    - Data retention policies?

14. **How are secrets managed?**
    - `.env` files in docker-compose (dev only)
    - Production: Kubernetes secrets? HashiCorp Vault? AWS Secrets Manager?

---

## 7. EVIDENCE-BASED CONCLUSIONS

### ✅ STRONG FOUNDATIONS (Reuse These)

1. **Backend Architecture** - Well-structured FastAPI app with proper separation of concerns
2. **Security Primitives** - Token encryption, HMAC verification implemented correctly
3. **Data Model** - Solid PostgreSQL schema with proper indexes and constraints
4. **Polaris UI** - Frontend follows Shopify design patterns correctly
5. **GraphQL Client** - Rate limiting and error handling done right

### ⚠️ CRITICAL GAPS (Must Fix for Production)

1. **No OAuth/Onboarding** - Can't add new shops
2. **Broken Sync** - sync_shop_data() doesn't exist
3. **No Webhooks** - Data goes stale immediately
4. **No Multi-Store** - Enterprise customers blocked

### 🗑️ BLOAT TO REMOVE (Simplify First)

1. **Code Analysis Feature** - 30% of codebase, completely unused
2. **Job Queue Infrastructure** - Complex, not needed yet
3. **Triple AI Provider Config** - No AI actually used in insights
4. **Redis** - Configured but not used

### 📈 ITERATION SPEED WINS

**Keep:**
- Repository pattern (testable)
- Demo mode (dev velocity)
- Structured logging (debuggability)
- Polaris components (polish)

**Remove:**
- Code analysis (distraction)
- Advanced analytics (premature)
- Notification service (not used)
- Traffic metrics (dead table)

**Fix:**
- Implement sync_shop_data()
- Add webhook handlers
- Document OAuth flow (or implement it)
- Add org_id for multi-store

---

## 8. RECOMMENDED NEXT ACTIONS

### 🚨 IMMEDIATE (Blocking Production)

1. Implement `backend/app/services/data_sync.py` with incremental sync logic
2. Create webhook router with handlers for orders/products/app events
3. Document or implement OAuth flow (currently opaque)
4. Remove commented-out code analysis feature (delete migrations, models, routers)

### 🔧 SHORT-TERM (Next Sprint)

5. Add `last_products_cursor`, `last_orders_cursor` to shops table
6. Create `order_line_items` normalized table for efficient queries
7. Add org/multi-store support (`organizations`, `organization_members` tables)
8. Implement proper error handling in sync flow with rollback

### 📊 MEDIUM-TERM (Next Quarter)

9. Replace demo mode with proper 404 errors in production
10. Add sync status visibility (progress, errors, last_sync_at)
11. Implement webhook deduplication (`webhook_events` table)
12. Add App Bridge SDK to frontend for true embedded app experience

---

**END OF ANALYSIS**

*This analysis is based on static code inspection as of 2026-02-04. Runtime behavior may differ.*
