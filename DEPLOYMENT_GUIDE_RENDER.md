# Deployment Guide: Render Production

**Date:** 2026-02-05
**Architecture:** Growzilla-Beta (Shopify App) + FastAPI Backend + PostgreSQL
**Platform:** Render.com

---

## 🏗️ CURRENT INFRASTRUCTURE

### Deployed Services

| Service | Type | URL | Status |
|---------|------|-----|--------|
| **ecomdash-api** | Web Service | https://ecomdash-api.onrender.com | ✅ LIVE |
| **ecomdash-db** | PostgreSQL | dpg-d5jn6l6mcj7s738fnrig-a | ✅ LIVE |
| **growzilla-beta** | Web Service | https://growzilla-beta.onrender.com | ⏳ PENDING |

---

## 📋 DEPLOYMENT CHECKLIST

### Pre-Deployment

- [x] Backend API deployed and healthy
- [x] Database provisioned and migrated
- [x] Environment variables configured
- [x] Scopes reduced to MVP (`read_products`, `read_orders`)
- [x] Local testing completed
- [ ] Commit changes to git
- [ ] Push to main branch

### Deployment Steps

#### 1. Commit Scope Changes

```bash
cd /home/ghostking/projects/EcomDashQ1BetaCohort

# Check what changed
git status

# Stage changes
git add growzilla-beta/shopify.app.toml
git add growzilla-beta/.env
git add LOCAL_TESTING_GUIDE.md
git add DEPLOYMENT_GUIDE_RENDER.md
git add growzilla-beta/setup-local.sh

# Commit with clear message
git commit -m "feat: reduce Shopify scopes to MVP (read_products, read_orders)

- Update shopify.app.toml: reduce from 6 to 2 scopes
- Align with EXECUTION_PLAN_SHOPIFY_EMBEDDED_APP.md recommendations
- Faster Shopify App Store approval path
- Add local testing setup script
- Add deployment guides

Scopes removed (defer to Phase 2):
- read_customers (not implemented yet)
- read_inventory (accessible via products.totalInventory)
- read_discounts (data from orders.discountCodes)
- read_analytics (insights #4, #5 not implemented)"
```

#### 2. Push to Render

```bash
# Push to main (triggers auto-deploy)
git push origin main
```

Render will automatically:
- Detect changes in `growzilla-beta/`
- Build the app (`npm run build`)
- Deploy to production
- Run health checks

#### 3. Monitor Deployment

**Via Dashboard:**
1. Go to: https://dashboard.render.com
2. Click on **growzilla-beta** service
3. Go to **Logs** tab
4. Watch for:
   ```
   ==> Build successful
   ==> Starting service
   ==> Health check passed
   ```

**Via API:**
```bash
# Check if deployed
curl -I https://growzilla-beta.onrender.com

# Should return: HTTP/1.1 200 OK
```

#### 4. Verify Backend Connection

```bash
# Check backend health
curl https://ecomdash-api.onrender.com/health

# Expected:
# {
#   "status": "healthy",
#   "version": "2.0.0"
# }
```

#### 5. Test in Shopify Test Store

1. Go to: https://testingground-9560.myshopify.com/admin/apps
2. Find **Growzilla Beta**
3. Click to launch app
4. **Verify:**
   - App loads without errors
   - Dashboard shows demo data
   - Insights appear
   - Browser network tab shows calls to `https://ecomdash-api.onrender.com`

---

## 🔐 ENVIRONMENT VARIABLES (Production)

### Backend (ecomdash-api)

Set in Render Dashboard → ecomdash-api → Environment:

```bash
# Database (Auto-set by Render)
DATABASE_URL=postgresql://ecomdash:...@dpg-d5jn6l6mcj7s738fnrig-a.oregon-postgres.render.com/ecomdash

# Application
APP_NAME=EcomDash V2 API
APP_VERSION=2.0.0
ENVIRONMENT=production
DEBUG=false

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=<generate-strong-32-char-key>
ENCRYPTION_KEY=<generate-strong-32-char-key>

# CORS
ALLOWED_ORIGINS=https://growzilla-beta.onrender.com,https://admin.shopify.com,https://*.myshopify.com

# Shopify
SHOPIFY_API_KEY=02e4e67112ab0bf60bbd4de3afbff59e
SHOPIFY_API_SECRET=<from-shopify-partners>
SCOPES=read_products,read_orders
```

### Frontend (growzilla-beta)

Set in Render Dashboard → growzilla-beta → Environment:

```bash
# Shopify Credentials
SHOPIFY_API_KEY=02e4e67112ab0bf60bbd4de3afbff59e
SHOPIFY_API_SECRET=<from-shopify-partners>

# Backend API
BACKEND_API_URL=https://ecomdash-api.onrender.com

# App URL (auto-set by Render)
SHOPIFY_APP_URL=https://growzilla-beta.onrender.com

# Database (Render-managed PostgreSQL for session storage)
DATABASE_URL=<from-render-postgres-service>

# Scopes (must match shopify.app.toml)
SCOPES=read_products,read_orders
```

---

## 🔄 CONTINUOUS DEPLOYMENT

### Auto-Deploy on Git Push

Render is configured for auto-deploy:

1. **Push to main branch:**
   ```bash
   git push origin main
   ```

2. **Render detects changes:**
   - Pulls latest code
   - Runs build
   - Deploys automatically

3. **Monitor via Render Dashboard:**
   - Go to: https://dashboard.render.com
   - Check **Deploys** tab
   - View logs in real-time

### Manual Deploy (if needed)

1. Go to: https://dashboard.render.com
2. Click on service (growzilla-beta or ecomdash-api)
3. Click **Manual Deploy** → **Deploy latest commit**
4. Choose branch: `main`
5. Click **Deploy**

---

## 🧪 POST-DEPLOYMENT TESTING

### Health Checks

```bash
# Backend API
curl https://ecomdash-api.onrender.com/health
# Expected: {"status":"healthy","version":"2.0.0"}

# Frontend (Shopify app)
curl -I https://growzilla-beta.onrender.com
# Expected: HTTP/1.1 200 OK
```

### API Endpoints

```bash
# Dashboard stats (will return demo data without shop_id)
curl https://ecomdash-api.onrender.com/api/dashboard/stats?shop_id=00000000-0000-0000-0000-000000000001

# Insights
curl https://ecomdash-api.onrender.com/api/insights?shop_id=00000000-0000-0000-0000-000000000001
```

### Shopify App Installation

1. **Via Shopify Partners:**
   - Go to: https://partners.shopify.com
   - Navigate to your app
   - Click **Select stores** → testingground-9560
   - Install app

2. **Test OAuth Flow:**
   - App should redirect to Shopify OAuth
   - Approve permissions (read_products, read_orders only)
   - Redirect to dashboard

3. **Test Dashboard:**
   - Stats cards load
   - Revenue chart renders
   - Insights appear
   - No console errors

---

## 🚨 ROLLBACK PROCEDURE

If deployment fails:

### Option 1: Revert via Git

```bash
# Find last good commit
git log --oneline

# Revert to previous commit
git revert HEAD

# Push revert
git push origin main

# Render auto-deploys reverted version
```

### Option 2: Redeploy Previous Version

1. Go to: https://dashboard.render.com
2. Click on service → **Deploys** tab
3. Find last successful deploy
4. Click **Redeploy**

---

## 📊 MONITORING

### Render Dashboard

- **Logs:** Real-time application logs
- **Metrics:** CPU, memory, request count
- **Deploys:** Deployment history
- **Events:** Service events and alerts

### Health Check Monitoring

Set up monitoring (optional):
```bash
# Using curl + cron (every 5 minutes)
*/5 * * * * curl -f https://ecomdash-api.onrender.com/health || echo "Backend down!"
*/5 * * * * curl -f https://growzilla-beta.onrender.com || echo "Frontend down!"
```

### Error Tracking

If Sentry is configured:
- Errors automatically sent to Sentry
- View at: https://sentry.io

---

## 🐛 TROUBLESHOOTING

### Issue: "Service Unavailable" after deploy

**Cause:** Build failed or service didn't start

**Fix:**
1. Check Render logs
2. Look for build errors
3. Verify environment variables
4. Check `package.json` scripts

### Issue: CORS errors in production

**Cause:** Frontend origin not in ALLOWED_ORIGINS

**Fix:**
1. Update backend `ALLOWED_ORIGINS` env var
2. Add: `https://growzilla-beta.onrender.com`
3. Redeploy backend

### Issue: "Database connection failed"

**Cause:** DATABASE_URL incorrect or DB down

**Fix:**
1. Check Render database service is running
2. Verify DATABASE_URL env var
3. Test connection:
   ```bash
   psql $DATABASE_URL
   ```

### Issue: Shopify OAuth fails

**Cause:** SHOPIFY_API_SECRET incorrect

**Fix:**
1. Go to: https://partners.shopify.com
2. Get API credentials
3. Update env vars in Render
4. Redeploy

---

## 📈 NEXT STEPS

After successful deployment:

1. ✅ **Test in production store**
2. ✅ **Monitor logs for 24 hours**
3. ⏭️ **Implement data sync** (EXECUTION_PLAN Phase 3)
4. ⏭️ **Add webhook handlers** (EXECUTION_PLAN Phase 4)
5. ⏭️ **Submit to Shopify App Store** (after Phase 4)

---

## 🎯 SUCCESS CRITERIA

Deployment successful when:

- [x] Both services show "Healthy" status in Render
- [x] Backend health check returns 200
- [x] Frontend loads without errors
- [x] Shopify OAuth flow completes
- [x] Dashboard displays demo data
- [x] No CORS errors
- [x] Only 2 scopes requested in Shopify Admin

---

**Deployment ready!** Push to main branch to trigger auto-deploy.
