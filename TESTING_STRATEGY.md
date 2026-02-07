# Testing Strategy - Shopify Embedded App Development

## Claude Code's Testing Capabilities

### ✅ What I CAN Test (Automated)

| Test Type | How I Test | What It Catches |
|-----------|-----------|----------------|
| **TypeScript Compilation** | `npm run build` | Type errors, missing imports, syntax errors |
| **Server Startup** | `npm run dev` + read logs | Port conflicts, env var issues, crash on boot |
| **Backend API** | `pytest -v`, `curl` requests | Endpoint errors, validation issues, DB failures |
| **Build Success** | `npm run build` exit code | Compilation failures, dependency issues |
| **Import Structure** | `tsc --noEmit` | Circular dependencies, wrong paths |
| **E2E Tests Setup** | Create Playwright tests | Test infrastructure ready for you to run |

### ❌ What I CANNOT Test (Requires Human)

| Test Type | Why I Can't | Who Should Test |
|-----------|-------------|----------------|
| **Visual UI Rendering** | No browser access | **YOU** - open http://localhost:3000 |
| **Navigation Clicks** | Can't interact with browser | **YOU** - click links, verify routes work |
| **Polaris Components** | Can't see rendered cards | **YOU** - verify cards display correctly |
| **App Bridge in iframe** | No Shopify Admin access | **YOU** - load in Shopify Admin |
| **Session Tokens** | Can't complete OAuth flow | **YOU** - install app, verify auth |
| **Browser Console** | Only see server logs | **YOU** - open DevTools, check for errors |

---

## Testing Workflow (Collaborative)

### **Step 1: I Write Code + Run Automated Tests**

For each change, I will:

```bash
# 1. Check TypeScript compiles
cd frontend
npm run build

# 2. Start dev server and check logs
npm run dev
# → I'll read output for errors like:
#    ✗ Failed to compile
#    ✓ Compiled successfully

# 3. Test backend API
cd backend
pytest -v
# → I'll verify all tests pass

# 4. Hit API endpoints
curl http://localhost:8000/api/dashboard/stats
# → I'll verify JSON response is valid
```

**I'll tell you:** "✅ TypeScript compiles, server starts, API responds"

---

### **Step 2: You Run E2E Tests (Browser Required)**

After I make changes, you should run:

```bash
cd frontend

# Install Playwright (first time only)
npm install -D @playwright/test
npx playwright install

# Run tests (starts dev server automatically)
npm run test:e2e

# Or run with UI to see what's happening
npm run test:e2e:ui

# Or run specific test
npx playwright test navigation.spec.ts
```

**Playwright will:**
- Start dev server (http://localhost:3000)
- Open browser (Chrome, Firefox, Safari)
- Navigate to dashboard
- Verify Polaris cards load
- Test navigation /dashboard → /insights
- Capture screenshots on failure
- Report results

**You'll see:** HTML report with pass/fail for each test

---

### **Step 3: Manual Verification Checklist**

Even with Playwright, you should manually check:

#### **Local Development (Standalone)**

Open browser: `http://localhost:3000`

- [ ] Dashboard loads without blank screen
- [ ] Stats cards show numbers (not "undefined")
- [ ] Revenue chart renders (not empty box)
- [ ] AI insight card displays text
- [ ] Click navigation → no white screen crash
- [ ] Browser console has no red errors (F12 → Console)

#### **Embedded in Shopify Admin**

Run: `shopify app dev`

Open: `https://{your-dev-store}.myshopify.com/admin/apps/{app-handle}`

- [ ] App loads in iframe (not blocked)
- [ ] TitleBar shows "Dashboard" (not default title)
- [ ] Navigation stays in iframe (doesn't break out)
- [ ] Session token is passed (check Network tab)
- [ ] API requests include Authorization header
- [ ] Data loads from backend (not demo data)

#### **Critical User Flows**

- [ ] Install app → OAuth completes → redirects to dashboard
- [ ] Click "Sync Now" → loading state → success message
- [ ] Navigate between all routes → no crashes
- [ ] Refresh page → state persists
- [ ] Uninstall app → data deleted (verify in DB)

---

## Test Scripts (Add to frontend/package.json)

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:debug": "playwright test --debug",
    "test:e2e:headed": "playwright test --headed"
  },
  "devDependencies": {
    "@playwright/test": "^1.40.0",
    "vitest": "^1.0.0"
  }
}
```

---

## Testing Schedule (Per Phase)

### **Phase 0: Bloat Removal**
- **I test:** Backend tests still pass, server starts
- **You test:** Nothing (no frontend changes)

### **Phase 1: App Bridge Integration**
- **I test:** TypeScript compiles, no import errors
- **You test:** 🔴 **CRITICAL** - App Bridge loads, `window.shopify` exists
- **Playwright:** Run `navigation.spec.ts` to verify no crashes

### **Phase 2: OAuth**
- **I test:** Backend OAuth endpoint responds, HMAC verification works
- **You test:** 🔴 **CRITICAL** - Full OAuth flow (install → callback → token stored)
- **Manual:** Install app via link, verify redirects work

### **Phase 3: Data Sync**
- **I test:** Sync endpoint returns 200, cursor logic works
- **You test:** Dashboard shows real data (not demo), verify in DB
- **Playwright:** Run API integration tests

### **Phase 4: Webhooks**
- **I test:** Webhook endpoints respond 200, HMAC verified
- **You test:** Send test webhook, verify DB updated
- **Tool:** Use Shopify CLI `shopify webhook trigger`

### **Phase 5: Dashboard**
- **I test:** Components compile, no PropTypes errors
- **You test:** 🔴 **CRITICAL** - All cards render, navigation works
- **Playwright:** Full navigation.spec.ts suite

### **Phase 6: Multi-Org**
- **I test:** API endpoints respond, DB queries work
- **You test:** Create org, add stores, switch between them
- **Manual:** Full multi-store workflow

---

## When Something Breaks

### **If I see compilation error:**
```
✗ [ERROR] Could not resolve "@shopify/app-bridge-react"
```
→ I'll fix: add dependency, update imports

### **If you see blank screen:**
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Check Network tab for failed API calls
4. Copy error message → tell me
5. I'll debug based on error

### **If Playwright test fails:**
1. Check `playwright-report/index.html` for screenshots
2. Run with `--headed` to see browser: `npm run test:e2e:headed`
3. Copy failure message → tell me
4. I'll fix the code

---

## Example Testing Session

**You:** "I ran the dev server, here's the output:"
```
[Claude makes changes]

You run:
```bash
cd frontend && npm run dev
```

Output:
```
VITE v5.0.0  ready in 234 ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
```

You open browser → http://localhost:3000

**You report back:**
- ✅ Dashboard loads
- ✅ Stats cards visible
- ❌ Revenue chart is blank (empty box)
- ❌ Console error: "Cannot read property 'data' of undefined"

**I respond:**
"The chart component expects `revenueChart.data` but it's undefined. Let me add a null check..."

[I fix the code]

**I tell you:**
"✅ Fixed. Please refresh and verify chart now renders."

---

## Bottom Line

**My role:** Write code, run automated checks, catch compilation errors
**Your role:** Verify UI looks correct, test user flows, check browser console
**Together:** Fast iteration with safety net

**Key Rule:** After EVERY phase milestone, you MUST manually test the critical path before we move to next phase.

---

## Quick Reference

```bash
# What I run automatically
npm run build          # TypeScript check
npm run dev            # Server startup check
pytest -v              # Backend tests
curl localhost:8000    # API smoke test

# What you should run
npm run test:e2e       # Playwright E2E tests
shopify app dev        # Test embedded app
# Then: open browser and click around
```

**If you see any errors, copy/paste them to me and I'll debug.**
