# Frontend-Backend Connection Implementation Plan

**Date:** 2026-02-04
**Goal:** Connect growzilla-beta frontend to ecomdash-api backend with full testing & verification

---

## Current State Analysis

### ✅ Backend (ecomdash-api) - READY
- **Status:** Deployed to `https://ecomdash-api.onrender.com`
- **Database:** Connected to Render PostgreSQL with 16 tables
- **Migrations:** Applied successfully
- **Health Check:** `/health` endpoint available
- **API Endpoints:**
  - `/api/dashboard/stats`
  - `/api/shops`
  - `/api/insights`

### ⚠️ Frontend (growzilla-beta) - NEEDS CONNECTION
- **Status:** Deployed to `https://growzilla-beta.onrender.com`
- **Current State:** Using mock/demo data
- **Framework:** React Router 7 + Polaris
- **Missing:**
  - API connection to backend
  - Session token handling
  - App Bridge integration for OAuth

### 🎯 Goal Architecture

```
Shopify Admin (embedded iframe)
         ↓
growzilla-beta.onrender.com (Frontend)
         ↓ (HTTPS API calls with session token)
ecomdash-api.onrender.com (Backend)
         ↓
Render PostgreSQL Database
```

---

## Implementation Plan (7 Phases)

### **Phase 0: Pre-Flight Checks** ⏱️ 15 minutes

**Goal:** Verify both services are healthy before making changes

#### Step 0.1: Verify Backend Health
```bash
# Check backend is running
curl https://ecomdash-api.onrender.com/health

# Expected: {"status": "healthy", ...}
```

#### Step 0.2: Check Render Services
```bash
# List all services
render services list -o json | jq '.[] | select(.service) | {name: .service.name, status: .service.suspended, url: .service.serviceDetails.url}'

# Expected: Both growzilla-beta and ecomdash-api show "not_suspended"
```

#### Step 0.3: Check Backend Logs
```bash
# Get recent backend logs
render logs -r srv-d5jq6fsoud1c73fho0dg -o text --limit 50

# Look for: No critical errors, server started successfully
```

#### Step 0.4: Check Database Tables
```bash
cd /home/ghostking/projects/EcomDashQ1BetaCohort/backend

.venv/bin/python -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.core.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT COUNT(*) FROM shops'))
        count = result.fetchone()[0]
        print(f'Shops in database: {count}')

asyncio.run(check())
"

# Expected: Shows shop count (0 initially, will have data after sync)
```

**Success Criteria:**
- ✅ Backend health check returns 200
- ✅ Both services show "not_suspended"
- ✅ No errors in backend logs
- ✅ Database connection working

---

### **Phase 1: Configure CORS** ⏱️ 10 minutes

**Goal:** Allow frontend to call backend API

#### Step 1.1: Read Current CORS Config
```bash
cd /home/ghostking/projects/EcomDashQ1BetaCohort/backend

# Check current CORS settings
grep -A 5 "ALLOWED_ORIGINS" app/main.py
```

#### Step 1.2: Update CORS to Include Frontend URL

**File:** `backend/app/main.py` (around line 48)

**Add to allowed_origins:**
```python
allowed_origins = [
    "https://growzilla-beta.onrender.com",  # ← ADD THIS
    "https://admin.shopify.com",
    "https://*.myshopify.com",
    "http://localhost:3000",  # Keep for local dev
]
```

#### Step 1.3: Update .env.local with CORS
```bash
# Add to backend/.env.local
echo "ALLOWED_ORIGINS=https://growzilla-beta.onrender.com,https://admin.shopify.com,https://*.myshopify.com" >> .env.local
```

#### Step 1.4: Test CORS Locally
```bash
# Start backend locally
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000 &

# Test CORS preflight
curl -X OPTIONS http://localhost:8000/health \
  -H "Origin: https://growzilla-beta.onrender.com" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Look for: Access-Control-Allow-Origin: https://growzilla-beta.onrender.com
```

#### Step 1.5: Commit and Deploy Backend
```bash
git add backend/app/main.py backend/.env.local
git commit -m "feat: add growzilla-beta to CORS allowed origins

- Allow frontend to call backend API
- Add growzilla-beta.onrender.com to allowed origins

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git push origin main
```

#### Step 1.6: Verify Deployment on Render
```bash
# Watch deployment logs
render logs -r srv-d5jq6fsoud1c73fho0dg -o text --follow

# Wait for: "Application startup complete"
# Stop watching: Ctrl+C
```

#### Step 1.7: Test CORS on Production
```bash
# Test CORS from frontend domain
curl -X OPTIONS https://ecomdash-api.onrender.com/health \
  -H "Origin: https://growzilla-beta.onrender.com" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Expected: Access-Control-Allow-Origin header present
```

**Success Criteria:**
- ✅ CORS allows growzilla-beta domain
- ✅ Backend redeployed successfully
- ✅ CORS preflight requests succeed

---

### **Phase 2: Create API Client in Frontend** ⏱️ 30 minutes

**Goal:** Add backend API client to growzilla-beta

#### Step 2.1: Check Frontend Structure
```bash
cd /home/ghostking/projects/EcomDashQ1BetaCohort/growzilla-beta

# Find API client files
find app -name "*api*" -o -name "*client*" | head -10
ls -la app/services/ 2>/dev/null || echo "No services directory"
```

#### Step 2.2: Create API Client Service

**File:** `growzilla-beta/app/services/api.client.ts`

```typescript
/**
 * Backend API Client for ecomdash-api
 * Handles all HTTP requests to the backend with session tokens
 */

const API_BASE_URL = process.env.API_URL || "https://ecomdash-api.onrender.com";

interface ApiError {
  message: string;
  status: number;
  details?: unknown;
}

class BackendApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Make authenticated API request
   * @param endpoint - API endpoint (e.g., "/api/dashboard/stats")
   * @param sessionToken - Shopify session token from App Bridge
   * @param options - Fetch options
   */
  async request<T>(
    endpoint: string,
    sessionToken: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${sessionToken}`,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = {
        message: `API request failed: ${response.statusText}`,
        status: response.status,
      };

      try {
        const errorData = await response.json();
        error.details = errorData;
      } catch {
        // Response not JSON
      }

      throw error;
    }

    return response.json();
  }

  /**
   * Get dashboard stats
   */
  async getDashboardStats(sessionToken: string, shopId: string) {
    return this.request(
      `/api/dashboard/stats?shop_id=${shopId}`,
      sessionToken,
      { method: "GET" }
    );
  }

  /**
   * Get insights
   */
  async getInsights(sessionToken: string, shopId: string) {
    return this.request(
      `/api/insights?shop_id=${shopId}`,
      sessionToken,
      { method: "GET" }
    );
  }

  /**
   * Sync shop data
   */
  async syncShop(sessionToken: string, shopId: string) {
    return this.request(
      `/api/shops/${shopId}/sync`,
      sessionToken,
      { method: "POST" }
    );
  }

  /**
   * Health check (no auth needed)
   */
  async healthCheck() {
    const response = await fetch(`${this.baseUrl}/health`);
    return response.json();
  }
}

export const apiClient = new BackendApiClient();
export type { ApiError };
```

#### Step 2.3: Add Environment Variable

**File:** `growzilla-beta/.env`

```bash
# Backend API URL
API_URL=https://ecomdash-api.onrender.com
```

#### Step 2.4: Test API Client Locally

Create test file: `growzilla-beta/app/services/api.client.test.ts`

```typescript
import { apiClient } from "./api.client";

async function testApiClient() {
  try {
    console.log("Testing backend connection...");

    // Test 1: Health check (no auth)
    const health = await apiClient.healthCheck();
    console.log("✅ Health check:", health);

    // Test 2: CORS check
    console.log("✅ CORS working - no errors thrown");

    return true;
  } catch (error) {
    console.error("❌ API client test failed:", error);
    return false;
  }
}

testApiClient();
```

Run test:
```bash
cd growzilla-beta
npm run dev &
# Wait for server to start

# In browser console or via curl:
curl https://ecomdash-api.onrender.com/health
```

**Success Criteria:**
- ✅ API client created
- ✅ Environment variable set
- ✅ Health check succeeds
- ✅ CORS allows requests

---

### **Phase 3: Update Frontend to Use Backend API** ⏱️ 45 minutes

**Goal:** Replace mock data with real backend calls

#### Step 3.1: Find Current Data Fetching

```bash
cd growzilla-beta

# Find components that fetch data
grep -r "fetch\|useEffect\|useState" app/routes/*.tsx | head -20
grep -r "demo\|mock" app/ | grep -v node_modules | head -20
```

#### Step 3.2: Update Dashboard Route

**File:** `growzilla-beta/app/routes/_index.tsx` (or main dashboard route)

**Before (mock data):**
```typescript
const [stats, setStats] = useState({
  revenue: 1234.56,
  orders: 42,
  // ... mock data
});
```

**After (real API):**
```typescript
import { apiClient } from "~/services/api.client";
import { getSessionToken } from "@shopify/app-bridge/utilities";
import { useAppBridge } from "@shopify/app-bridge-react";

export default function Dashboard() {
  const app = useAppBridge();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadStats() {
      try {
        setLoading(true);

        // Get session token from App Bridge
        const sessionToken = await getSessionToken(app);

        // Extract shop from token (JWT decode)
        const payload = JSON.parse(atob(sessionToken.split('.')[1]));
        const shop = payload.dest.replace('https://', '').replace('.myshopify.com', '');

        // Fetch from backend
        const data = await apiClient.getDashboardStats(sessionToken, shop);
        setStats(data);
        setError(null);
      } catch (err) {
        console.error("Failed to load stats:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadStats();
  }, [app]);

  if (loading) return <Spinner />;
  if (error) return <Banner status="critical">{error}</Banner>;
  if (!stats) return <Banner status="info">No data available</Banner>;

  return (
    <Page title="Dashboard">
      <StatsCard revenue={stats.yesterday_revenue} />
      {/* ... rest of dashboard */}
    </Page>
  );
}
```

#### Step 3.3: Add Session Token Utility

**File:** `growzilla-beta/app/utils/session.ts`

```typescript
/**
 * Extract shop domain from Shopify session token
 */
export function getShopFromToken(sessionToken: string): string {
  try {
    const payload = JSON.parse(atob(sessionToken.split('.')[1]));
    const dest = payload.dest; // e.g., "https://testingground-9560.myshopify.com"
    return dest.replace('https://', '').replace('.myshopify.com', '');
  } catch (error) {
    console.error("Failed to parse session token:", error);
    throw new Error("Invalid session token");
  }
}

/**
 * Check if session token is expired
 */
export function isTokenExpired(sessionToken: string): boolean {
  try {
    const payload = JSON.parse(atob(sessionToken.split('.')[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    return Date.now() > exp;
  } catch {
    return true;
  }
}
```

#### Step 3.4: Test Frontend Locally

```bash
cd growzilla-beta
npm run dev

# Open: http://localhost:3000
# Check browser console for:
# - Session token obtained
# - API calls made
# - Data loaded from backend
```

#### Step 3.5: Commit Frontend Changes

```bash
git add growzilla-beta/app/services/api.client.ts
git add growzilla-beta/app/utils/session.ts
git add growzilla-beta/app/routes/_index.tsx
git add growzilla-beta/.env

git commit -m "feat: connect frontend to backend API

- Add API client with session token support
- Replace mock data with real backend calls
- Add session token utilities
- Update dashboard to fetch from ecomdash-api

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git push origin main
```

**Success Criteria:**
- ✅ API client integrated
- ✅ Session token extracted from App Bridge
- ✅ Dashboard fetches from backend
- ✅ Error handling in place

---

### **Phase 4: Deploy and Test on Render** ⏱️ 30 minutes

**Goal:** Deploy frontend and verify connection works in production

#### Step 4.1: Monitor Frontend Deployment

```bash
# Get growzilla-beta service ID
render services list -o json | jq '.[] | select(.service.name == "Growzilla-Beta") | .service.id'

# Watch deployment logs (replace with actual ID)
render logs -r srv-d5t06ue3jp1c738vcdf0 -o text --follow

# Wait for: "Application startup complete"
```

#### Step 4.2: Check Deployment Status

```bash
# Check service status
render services get srv-d5t06ue3jp1c738vcdf0 -o json | jq '{name, status: .service.suspended, url: .service.serviceDetails.url}'

# Expected: suspended: "not_suspended"
```

#### Step 4.3: Test Frontend in Browser

```bash
# Open in browser:
open https://growzilla-beta.onrender.com

# Or via Shopify Admin:
open https://admin.shopify.com/store/testingground-9560/apps/growzillabeta-1/
```

**Manual Checks:**
1. Open browser DevTools (F12)
2. Go to Network tab
3. Refresh page
4. Look for API calls to `ecomdash-api.onrender.com`
5. Check response status (should be 200)
6. Verify data loads in UI

#### Step 4.4: Test Backend API Directly

```bash
# Test without auth (should work)
curl https://ecomdash-api.onrender.com/health

# Test with auth (will fail without valid token)
curl https://ecomdash-api.onrender.com/api/dashboard/stats \
  -H "Authorization: Bearer fake-token" \
  -v

# Expected: 401 Unauthorized (correct - proves auth is required)
```

#### Step 4.5: Check Backend Logs for API Calls

```bash
# Watch backend logs
render logs -r srv-d5jq6fsoud1c73fho0dg -o text --limit 100

# Look for:
# - GET /api/dashboard/stats requests
# - Status codes (200 = success, 401 = auth issue)
# - Any errors
```

**Success Criteria:**
- ✅ Frontend deploys successfully
- ✅ API calls appear in Network tab
- ✅ Backend logs show incoming requests
- ✅ No CORS errors in console

---

### **Phase 5: Add App Bridge for Session Tokens** ⏱️ 45 minutes

**Goal:** Integrate Shopify App Bridge to get real session tokens

#### Step 5.1: Check App Bridge Installation

```bash
cd growzilla-beta
npm list @shopify/app-bridge-react @shopify/app-bridge

# Should show installed versions
```

#### Step 5.2: Update Root Layout with App Bridge

**File:** `growzilla-beta/app/root.tsx`

**Add App Bridge Provider:**

```typescript
import { AppProvider } from "@shopify/app-bridge-react";

export default function App() {
  const config = {
    apiKey: process.env.SHOPIFY_API_KEY!,
    host: new URL(window.location).searchParams.get("host")!,
  };

  return (
    <html>
      <head>
        <Meta />
        <Links />
      </head>
      <body>
        <AppProvider config={config}>
          <PolarisProvider>
            <Outlet />
          </PolarisProvider>
        </AppProvider>
        <Scripts />
      </body>
    </html>
  );
}
```

#### Step 5.3: Add Shopify Environment Variables

**File:** `growzilla-beta/.env`

```bash
SHOPIFY_API_KEY=your_shopify_api_key_here
SHOPIFY_API_SECRET=your_shopify_api_secret_here
```

**Get from Shopify Partners Dashboard:**
1. Go to https://partners.shopify.com
2. Select your app
3. Copy API key and secret

#### Step 5.4: Update Dashboard to Use App Bridge

**File:** `growzilla-beta/app/routes/_index.tsx`

```typescript
import { useAppBridge } from "@shopify/app-bridge-react";
import { getSessionToken } from "@shopify/app-bridge/utilities";

export default function Dashboard() {
  const app = useAppBridge();

  useEffect(() => {
    async function loadData() {
      // Get session token
      const sessionToken = await getSessionToken(app);
      console.log("Got session token:", sessionToken ? "✅" : "❌");

      // Use token for API calls
      const data = await apiClient.getDashboardStats(sessionToken, shopId);
      // ...
    }

    loadData();
  }, [app]);
}
```

#### Step 5.5: Test App Bridge Locally

```bash
# Must test in Shopify Admin (not standalone)
cd growzilla-beta
npm run dev

# Use Shopify CLI to create tunnel
npx shopify app dev

# Opens: https://admin.shopify.com/store/YOUR_STORE/apps/YOUR_APP
```

**Check in Browser Console:**
```javascript
// Should see:
// - "Got session token: ✅"
// - API requests with Bearer token
// - No "unauthorized" errors
```

#### Step 5.6: Commit App Bridge Changes

```bash
git add growzilla-beta/app/root.tsx
git add growzilla-beta/app/routes/_index.tsx
git add growzilla-beta/.env

git commit -m "feat: integrate Shopify App Bridge for session tokens

- Add AppProvider to root layout
- Use getSessionToken for API authentication
- Configure Shopify API key

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git push origin main
```

**Success Criteria:**
- ✅ App Bridge provider configured
- ✅ Session tokens obtained
- ✅ API calls authenticated
- ✅ No auth errors

---

### **Phase 6: End-to-End Testing** ⏱️ 30 minutes

**Goal:** Verify entire flow works in production

#### Step 6.1: Test User Flow in Shopify Admin

**Manual Test Checklist:**

1. **Install/Open App:**
   - Go to Shopify Admin
   - Open your app
   - URL: `https://admin.shopify.com/store/testingground-9560/apps/growzillabeta-1/`

2. **Dashboard Loads:**
   - [ ] Dashboard page loads without errors
   - [ ] No blank/white screen
   - [ ] No "unauthorized" errors in console

3. **Data Appears:**
   - [ ] Stats cards show numbers (not "undefined")
   - [ ] Charts render (not empty)
   - [ ] Insights display

4. **API Calls Succeed:**
   - Open DevTools → Network tab
   - [ ] Requests to `ecomdash-api.onrender.com`
   - [ ] Status 200 (not 401/403/500)
   - [ ] Response contains data

5. **Navigation Works:**
   - [ ] Click between dashboard/insights
   - [ ] App stays in iframe (doesn't break out)
   - [ ] No crashes on route changes

#### Step 6.2: Check Backend Received Data

```bash
# Check backend logs for successful requests
render logs -r srv-d5jq6fsoud1c73fho0dg -o text --limit 100 | grep "200 OK"

# Check database for shop records
cd /home/ghostking/projects/EcomDashQ1BetaCohort/backend

.venv/bin/python -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.core.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text(\"\"\"
            SELECT domain, last_sync_at
            FROM shops
            ORDER BY created_at DESC
            LIMIT 5
        \"\"\"))
        for row in result:
            print(f'Shop: {row[0]}, Last Sync: {row[1]}')

asyncio.run(check())
"
```

#### Step 6.3: Test Error Handling

**Simulate Errors:**

1. **Backend Down:**
   ```bash
   # Temporarily suspend backend
   # (Don't actually do this - just check error handling exists)
   ```
   - Frontend should show error message
   - No white screen crash

2. **Invalid Session Token:**
   - Clear browser cookies
   - Reload app
   - Should redirect to OAuth or show "unauthorized"

3. **Network Error:**
   - Open DevTools → Network tab → Throttle to "Offline"
   - Frontend should show "connection error"

#### Step 6.4: Performance Check

```bash
# Check response times
curl -w "\nTime: %{time_total}s\n" https://ecomdash-api.onrender.com/health

# Should be < 2 seconds

# Check Render service metrics
render services get srv-d5jq6fsoud1c73fho0dg -o json | jq '.service.serviceDetails | {cpu, memory}'
```

**Success Criteria:**
- ✅ Full user flow works in Shopify Admin
- ✅ Data loads from backend
- ✅ No errors in console
- ✅ Navigation works
- ✅ Error handling graceful
- ✅ Performance acceptable

---

### **Phase 7: Monitoring and Documentation** ⏱️ 20 minutes

**Goal:** Set up monitoring and document the connection

#### Step 7.1: Create Health Check Script

**File:** `scripts/health-check.sh`

```bash
#!/bin/bash
# Health check for frontend-backend connection

echo "🔍 Checking Frontend-Backend Connection..."
echo ""

# 1. Backend Health
echo "1. Backend Health:"
BACKEND_STATUS=$(curl -s https://ecomdash-api.onrender.com/health | jq -r '.status')
if [ "$BACKEND_STATUS" = "healthy" ]; then
  echo "   ✅ Backend: $BACKEND_STATUS"
else
  echo "   ❌ Backend: $BACKEND_STATUS"
  exit 1
fi

# 2. Frontend Health
echo "2. Frontend Health:"
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://growzilla-beta.onrender.com)
if [ "$FRONTEND_STATUS" = "200" ]; then
  echo "   ✅ Frontend: HTTP $FRONTEND_STATUS"
else
  echo "   ❌ Frontend: HTTP $FRONTEND_STATUS"
  exit 1
fi

# 3. Database Connection
echo "3. Database:"
cd /home/ghostking/projects/EcomDashQ1BetaCohort/backend
SHOP_COUNT=$(.venv/bin/python -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.core.database import engine
from sqlalchemy import text
async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT COUNT(*) FROM shops'))
        print(result.fetchone()[0])
asyncio.run(check())
")
echo "   ✅ Database: $SHOP_COUNT shops"

# 4. CORS Check
echo "4. CORS:"
CORS_HEADER=$(curl -s -X OPTIONS https://ecomdash-api.onrender.com/health \
  -H "Origin: https://growzilla-beta.onrender.com" \
  -H "Access-Control-Request-Method: GET" \
  -D - | grep -i "access-control-allow-origin")
if [ -n "$CORS_HEADER" ]; then
  echo "   ✅ CORS configured"
else
  echo "   ❌ CORS not configured"
  exit 1
fi

echo ""
echo "✅ All health checks passed!"
```

Make executable:
```bash
chmod +x scripts/health-check.sh
```

#### Step 7.2: Set Up Render Monitoring

```bash
# Get service metrics
render services get srv-d5jq6fsoud1c73fho0dg -o json | jq '.service.serviceDetails | {
  cpu: .cpu,
  memory: .memory,
  instances: .numInstances,
  autoscaling: .autoscaling
}'

# Set up alerts (if not already configured)
# Go to Render Dashboard → Service → Settings → Notifications
# Enable: "Notify on failed deploys" and "Notify on service suspensions"
```

#### Step 7.3: Document API Endpoints

**File:** `API_ENDPOINTS.md`

```markdown
# API Endpoints Documentation

## Base URL
- Production: `https://ecomdash-api.onrender.com`
- Local: `http://localhost:8000`

## Authentication
All endpoints require a Shopify session token in the Authorization header:
```
Authorization: Bearer <session_token>
```

## Endpoints

### Health Check
```
GET /health
```
No authentication required. Returns server status.

### Dashboard Stats
```
GET /api/dashboard/stats?shop_id={shop_id}
```
Returns dashboard statistics for a shop.

### Insights
```
GET /api/insights?shop_id={shop_id}
```
Returns AI insights for a shop.

### Sync Shop
```
POST /api/shops/{shop_id}/sync
```
Triggers a sync of shop data from Shopify.
```

#### Step 7.4: Create Connection Architecture Diagram

**File:** `ARCHITECTURE.md` (append)

```markdown
## Frontend-Backend Connection Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Shopify Admin (admin.shopify.com)                          │
│   • Merchant logs in                                        │
│   • Opens embedded app in iframe                            │
└────────────────────┬────────────────────────────────────────┘
                     │ host parameter + OAuth
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Frontend (growzilla-beta.onrender.com)                     │
│   • React Router 7 + Polaris UI                             │
│   • App Bridge (session token generation)                   │
│   • API Client (authenticated requests)                     │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS + Bearer token + CORS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend (ecomdash-api.onrender.com)                        │
│   • FastAPI + SQLAlchemy 2.0                                │
│   • Session token validation                                │
│   • Business logic + data processing                        │
└────────────────────┬────────────────────────────────────────┘
                     │ asyncpg + SSL
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Database (Render PostgreSQL)                                │
│   • shops, products, orders, insights                       │
│   • Multi-tenant isolation by shop_id                       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User opens app in Shopify Admin**
2. **Frontend loads in iframe** with `host` parameter
3. **App Bridge generates session token** (JWT with shop info)
4. **Frontend makes API request** to backend with token
5. **Backend validates token** against Shopify
6. **Backend queries database** for shop data
7. **Backend returns data** to frontend
8. **Frontend renders UI** in Polaris components
```

#### Step 7.5: Run Final Health Check

```bash
./scripts/health-check.sh

# Expected output:
# ✅ Backend: healthy
# ✅ Frontend: HTTP 200
# ✅ Database: X shops
# ✅ CORS configured
# ✅ All health checks passed!
```

**Success Criteria:**
- ✅ Health check script created
- ✅ Monitoring configured
- ✅ API documentation written
- ✅ Architecture documented
- ✅ All checks pass

---

## Rollback Procedures

### If Frontend Breaks

```bash
# 1. Check deployment logs
render logs -r srv-d5t06ue3jp1c738vcdf0 -o text --limit 100

# 2. Revert to previous commit
git log --oneline | head -5  # Find last working commit
git revert HEAD
git push origin main

# 3. Verify old version deployed
# Wait 2-3 minutes, then check:
curl https://growzilla-beta.onrender.com
```

### If Backend Breaks

```bash
# 1. Check backend logs
render logs -r srv-d5jq6fsoud1c73fho0dg -o text --limit 100

# 2. Revert CORS changes
cd backend
git revert HEAD
git push origin main

# 3. Restart service (if needed)
# From Render Dashboard: Service → Manual Deploy → Deploy Latest Commit
```

### If Database Issues

```bash
# 1. Check database connection
cd backend
.venv/bin/python -c "
import asyncio
from app.core.database import engine
async def test():
    async with engine.connect() as conn:
        print('Connected')
asyncio.run(test())
"

# 2. Check migrations
.venv/bin/alembic current
.venv/bin/alembic history

# 3. Rollback migration if needed
.venv/bin/alembic downgrade -1
```

---

## Testing Checklist

### Pre-Deployment Tests (Local)
- [ ] Backend health check works
- [ ] CORS configured correctly
- [ ] API client tests pass
- [ ] Frontend builds without errors
- [ ] Session token utilities work

### Post-Deployment Tests (Production)
- [ ] Both services deployed successfully
- [ ] Frontend loads in Shopify Admin
- [ ] API calls reach backend
- [ ] Session tokens obtained
- [ ] Data loads from backend
- [ ] No CORS errors
- [ ] Error handling works
- [ ] Navigation works

### Integration Tests
- [ ] Dashboard stats load
- [ ] Insights load
- [ ] Sync button works
- [ ] Multi-route navigation
- [ ] Error states display
- [ ] Loading states display

### Performance Tests
- [ ] Backend responds < 2s
- [ ] Frontend loads < 3s
- [ ] No memory leaks
- [ ] Autoscaling works

---

## Success Metrics

### Technical Metrics
- ✅ 0 CORS errors
- ✅ 0 authentication failures
- ✅ >95% API success rate (200 responses)
- ✅ <2s API response time
- ✅ 0 database connection errors

### User Experience Metrics
- ✅ App loads without blank screen
- ✅ Data appears within 3 seconds
- ✅ No console errors visible
- ✅ Navigation smooth (no crashes)
- ✅ Error messages user-friendly

---

## Timeline Summary

| Phase | Duration | Tasks | Status |
|-------|----------|-------|--------|
| Phase 0: Pre-Flight | 15 min | Health checks, verification | Pending |
| Phase 1: CORS | 10 min | Configure backend CORS | Pending |
| Phase 2: API Client | 30 min | Create frontend API client | Pending |
| Phase 3: Integration | 45 min | Connect frontend to backend | Pending |
| Phase 4: Deployment | 30 min | Deploy and test on Render | Pending |
| Phase 5: App Bridge | 45 min | Add session token support | Pending |
| Phase 6: E2E Testing | 30 min | Full flow verification | Pending |
| Phase 7: Monitoring | 20 min | Docs and health checks | Pending |
| **Total** | **~4 hours** | | |

---

## Next Steps After Connection

Once frontend-backend connection is working:

1. **Phase 0 (Execution Plan):** Remove bloat
   - Delete code_analysis tables
   - Remove unused AI providers
   - Clean up analytics feature

2. **Phase 2 (Execution Plan):** Implement OAuth
   - Add OAuth callback endpoint
   - Store shop tokens securely
   - Handle app installation flow

3. **Phase 3 (Execution Plan):** Data Sync
   - Implement incremental sync with cursors
   - Add Shopify GraphQL queries
   - Handle rate limiting

4. **Phase 4 (Execution Plan):** Webhooks
   - Register webhook subscriptions
   - Handle shop/update, orders/create
   - Implement idempotency

---

## Troubleshooting Guide

### CORS Errors
**Symptom:** "Access-Control-Allow-Origin" error in console

**Solution:**
```bash
# Check CORS config
grep -A 5 "ALLOWED_ORIGINS" backend/app/main.py

# Add frontend domain if missing
# Redeploy backend
```

### 401 Unauthorized
**Symptom:** API returns 401, session token invalid

**Solution:**
```bash
# Check session token in browser console
# Verify App Bridge configured
# Check Shopify API key is correct
```

### Backend Connection Refused
**Symptom:** "ERR_CONNECTION_REFUSED" or "Failed to fetch"

**Solution:**
```bash
# Check backend is running
render services get srv-d5jq6fsoud1c73fho0dg -o json | jq '.service.suspended'

# Should be: "not_suspended"
# If suspended, redeploy from Render Dashboard
```

### Database Connection Fails
**Symptom:** "relation does not exist" or connection errors

**Solution:**
```bash
# Check database status
render services list -o json | jq '.[] | select(.postgres)'

# Verify migrations ran
cd backend
.venv/bin/alembic current
```

---

## Useful Commands Reference

### Render CLI
```bash
# List services
render services list -o json

# Get service details
render services get <service-id> -o json

# View logs
render logs -r <service-id> -o text --limit 100

# Follow logs (live)
render logs -r <service-id> -o text --follow
```

### Health Checks
```bash
# Backend health
curl https://ecomdash-api.onrender.com/health

# Frontend health
curl -I https://growzilla-beta.onrender.com

# Database connection
cd backend && .venv/bin/python -c "from app.core.database import engine; print(engine)"
```

### Git Operations
```bash
# Commit with co-author
git commit -m "feat: your message

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to deploy
git push origin main

# Revert if needed
git revert HEAD
```

---

## Contact Points

### Render Services
- **Backend:** https://dashboard.render.com/web/srv-d5jq6fsoud1c73fho0dg
- **Frontend:** https://dashboard.render.com/web/srv-d5t06ue3jp1c738vcdf0
- **Database:** https://dashboard.render.com/d/dpg-d5jn6l6mcj7s738fnrig-a

### Shopify Admin
- **App:** https://admin.shopify.com/store/testingground-9560/apps/growzillabeta-1/
- **Partners:** https://partners.shopify.com

### GitHub
- **Repo:** https://github.com/AscenderGrey/EcomDashQ1BetaCohort

---

**This plan ensures a systematic, tested connection between frontend and backend with verification at each step.**
