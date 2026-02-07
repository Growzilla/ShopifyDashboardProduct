# Local Testing Guide: Growzilla-Beta ↔ Render Backend

**Date:** 2026-02-05
**Status:** Ready for testing
**Architecture:** Shopify embedded app (local) → FastAPI backend (Render)

---

## ✅ PRE-REQUISITES

- [x] Backend deployed on Render: `https://ecomdash-api.onrender.com`
- [x] PostgreSQL database on Render (live)
- [x] Test Shopify store: `testingground-9560.myshopify.com`
- [x] Shopify app credentials configured
- [x] Node.js 20+ installed
- [x] Scopes reduced to MVP (`read_products`, `read_orders`)

---

## 🚀 LOCAL SETUP (5 minutes)

### Step 1: Setup growzilla-beta

```bash
cd growzilla-beta
./setup-local.sh
```

This will:
- Install npm dependencies
- Generate Prisma client
- Run migrations for session storage (SQLite)
- Create `dev.db` file for storing Shopify OAuth sessions

### Step 2: Start Shopify Dev Server

```bash
npm run dev
```

This will:
- Start the Shopify CLI development server
- Create a tunnel (Cloudflare/ngrok) for webhooks
- Give you an installation URL like:
  ```
  https://testingground-9560.myshopify.com/admin/apps/growzillabeta-1234
  ```

### Step 3: Install in Test Store

1. Click the provided URL
2. Shopify will ask you to approve permissions:
   - ✅ Read products
   - ✅ Read orders
3. Click "Install"
4. You'll be redirected to the dashboard

---

## 🧪 TESTING CHECKLIST

### Test 1: Health Check

**Verify backend is live:**
```bash
curl https://ecomdash-api.onrender.com/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

### Test 2: OAuth Flow

1. Install app in test store (see Step 3 above)
2. **Check browser network tab:**
   - Should see POST to `/api/shops` with Shopify credentials
   - Backend returns shop record with UUID
3. **Check session storage:**
   - Run: `sqlite3 growzilla-beta/dev.db "SELECT * FROM Session;"`
   - Should see session record with shop domain and access token

### Test 3: Dashboard Loads

1. After OAuth, dashboard should load automatically
2. **Expected behavior:**
   - Stats cards show demo data (backend demo mode)
   - Revenue chart displays (7-day data)
   - ONE insight appears at top
3. **Check browser network tab:**
   - All API calls go to `https://ecomdash-api.onrender.com/api/*`
   - NOT to localhost:8000
   - Status: 200 OK

### Test 4: API Routes

Open browser DevTools → Network tab, then verify:

| Endpoint | Method | Expected Status | Data Source |
|----------|--------|-----------------|-------------|
| `/api/shops` | POST | 201 Created | Registers shop |
| `/api/dashboard/stats?shop_id=` | GET | 200 OK | Demo stats |
| `/api/dashboard/revenue-chart?shop_id=` | GET | 200 OK | Demo chart |
| `/api/insights?shop_id=` | GET | 200 OK | Demo insights |

### Test 5: Scope Verification

1. In Shopify Admin → Apps → Growzilla Beta → "About this app"
2. **Verify permissions show only:**
   - ✅ Read products
   - ✅ Read orders
3. **Should NOT show:**
   - ❌ Read customers
   - ❌ Read analytics
   - ❌ Read discounts
   - ❌ Read inventory

---

## 🐛 TROUBLESHOOTING

### Issue: "Failed to fetch" errors

**Cause:** Backend is down or CORS misconfigured

**Fix:**
```bash
# Check backend health
curl https://ecomdash-api.onrender.com/health

# Check CORS settings in backend/.env.local
# Should include: ALLOWED_ORIGINS=https://growzilla-beta.onrender.com,https://admin.shopify.com
```

### Issue: "Invalid session token"

**Cause:** Shopify session expired or session storage misconfigured

**Fix:**
```bash
# Regenerate Prisma client
cd growzilla-beta
npx prisma generate

# Restart dev server
npm run dev
```

### Issue: "Shop not found" errors

**Cause:** Shop not registered in backend database

**Fix:**
1. Uninstall app from test store
2. Reinstall via `npm run dev` URL
3. OAuth flow will re-register shop

### Issue: CORS errors in browser console

**Cause:** Missing origin in backend CORS config

**Fix:**
Check `backend/.env.local`:
```bash
ALLOWED_ORIGINS=https://growzilla-beta.onrender.com,https://admin.shopify.com,http://localhost:3000
```

Add the Shopify CLI tunnel URL if needed (check terminal output).

---

## 📊 EXPECTED BEHAVIOR

### Demo Mode

Since you don't have real order/product data synced yet:

- **Dashboard Stats:** Shows demo data (revenue, orders, AOV)
- **Revenue Chart:** Shows 7 days of mock data
- **Insights:** Shows ONE demo insight
- **API Calls:** All succeed with 200 status
- **Banner:** May show "Using mock data" message

This is **normal and expected** for initial testing!

### Real Data (After Sync)

Once you implement data sync (Phase 3 of EXECUTION_PLAN):
- Dashboard will show actual Shopify data
- Revenue chart will use real orders
- Insights engine will analyze real products/orders

---

## 🚀 DEPLOYMENT TO RENDER

### When Local Testing Passes:

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: reduce scopes to MVP (read_products, read_orders)"
   ```

2. **Push to main:**
   ```bash
   git push origin main
   ```

3. **Render auto-deploys:**
   - Monitor: https://dashboard.render.com
   - Check logs for deployment success
   - Verify: `https://growzilla-beta.onrender.com/health`

4. **Update Shopify app URL:**
   - Shopify Partners → Apps → Growzilla Beta
   - Ensure "App URL" is set to: `https://growzilla-beta.onrender.com`

5. **Test in production:**
   - Install app in test store via production URL
   - Verify OAuth, dashboard, insights all work
   - Check browser network tab (calls to production backend)

---

## 📝 NEXT STEPS (Post-Testing)

After successful local testing:

1. ✅ **Commit scope changes** to git
2. ✅ **Deploy to Render** (auto-deploy on push)
3. ⏭️ **Phase 3: Implement Data Sync** (EXECUTION_PLAN Phase 3)
   - Add `/api/shops/{id}/sync` endpoint
   - Implement incremental cursor tracking
   - Sync products and orders from Shopify
4. ⏭️ **Phase 4: Add Webhook Handlers** (EXECUTION_PLAN Phase 4)
   - `/webhooks/app/uninstalled`
   - `/webhooks/orders/create`
   - `/webhooks/orders/updated`
   - `/webhooks/products/update`

---

## 🎯 SUCCESS CRITERIA

Local testing is successful when:

- [x] Shopify CLI dev server starts without errors
- [x] App installs in test store
- [x] OAuth flow completes successfully
- [x] Dashboard loads with demo data
- [x] All API calls return 200 status
- [x] Browser network tab shows requests to `https://ecomdash-api.onrender.com`
- [x] Only 2 scopes requested (`read_products`, `read_orders`)
- [x] No CORS errors in browser console

---

## 📞 SUPPORT

If issues persist:

1. Check backend logs: https://dashboard.render.com → ecomdash-api → Logs
2. Check frontend terminal output for Shopify CLI errors
3. Inspect browser DevTools → Console for JavaScript errors
4. Verify `.env` files have correct URLs

---

**Ready to test!** Run `./setup-local.sh` in the `growzilla-beta/` directory to begin.
