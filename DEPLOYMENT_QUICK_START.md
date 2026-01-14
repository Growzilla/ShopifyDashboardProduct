# EcomDash V2 - Quick Start Deployment Guide

**TL;DR:** Deploy EcomDash to Render.com in under 30 minutes.

---

## Prerequisites (5 minutes)

1. **Render Account:** Sign up at [render.com](https://render.com) (free)
2. **GitHub Repository:** Fork or clone this repo
3. **Shopify Partners:** Create account at [partners.shopify.com](https://partners.shopify.com)
4. **OpenAI API Key:** Get from [platform.openai.com](https://platform.openai.com)

---

## Deployment Steps (10 minutes)

### 1. Connect GitHub to Render

```bash
# Push your code to GitHub
git push origin main
```

- Go to [dashboard.render.com](https://dashboard.render.com)
- Click **New +** → **Blueprint**
- Select your repository
- Branch: `main`
- Click **Apply**

Render will provision:
- ✅ ecomdash-api (FastAPI backend)
- ✅ ecomdash-worker (Background jobs)
- ✅ ecomdash-frontend (React UI)
- ✅ ecomdash-db (PostgreSQL)
- ✅ ecomdash-redis (Redis cache)

Wait 5-10 minutes for deployment.

### 2. Set Environment Variables (5 minutes)

Go to **Environment** → **Environment Groups** → **ecomdash-secrets**

Add these required secrets:

```bash
# From Shopify Partners Dashboard → Apps → Your App → App credentials
SHOPIFY_API_KEY=your_api_key_here
SHOPIFY_API_SECRET=your_api_secret_here

# From OpenAI Platform → API Keys
OPENAI_API_KEY=sk-your_openai_key_here

# Optional but recommended
RESEND_API_KEY=re_your_resend_key_here  # For emails
SENTRY_DSN=https://...@sentry.io/...    # For error tracking
```

Click **Save Changes** - this will trigger a redeploy.

### 3. Initialize Database (5 minutes)

```bash
# Install Render CLI
brew install render  # macOS
# or download from https://render.com/docs/cli

# Login
render login

# Open database shell
render psql ecomdash-db

# Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q

# Migrations run automatically via preDeployCommand in render.yaml
# Verify: Check logs for "alembic upgrade head"
render logs ecomdash-api --tail | grep alembic
```

### 4. Configure Shopify App (5 minutes)

Go to [partners.shopify.com](https://partners.shopify.com) → Your App:

**App URLs:**
- **App URL:** `https://ecomdash-api.onrender.com`
- **Allowed redirection URLs:**
  ```
  https://ecomdash-api.onrender.com/auth/callback
  https://ecomdash-frontend.onrender.com/auth/callback
  ```

**Update Environment Variable:**
Go to Render → ecomdash-api → Environment → Add:
```bash
SHOPIFY_APP_URL=https://ecomdash-api.onrender.com
```

---

## Verification (5 minutes)

### Test Health Check
```bash
curl https://ecomdash-api.onrender.com/health
# Expected: {"status":"healthy","version":"2.0.0","environment":"production"}
```

### Test Database Connection
```bash
render psql ecomdash-db -c "SELECT count(*) FROM shops;"
# Expected: 0 (no shops yet)
```

### Install on Test Store
1. Create development store in Shopify Partners
2. Install your app
3. Complete OAuth flow
4. Verify shop appears in database:
   ```bash
   render psql ecomdash-db -c "SELECT domain, created_at FROM shops;"
   ```

### Check Logs
```bash
# API logs
render logs ecomdash-api --tail

# Worker logs
render logs ecomdash-worker --tail
```

---

## Post-Deployment

### Set Up Monitoring (Optional but Recommended)

**1. Uptime Monitoring:**
- Sign up at [uptimerobot.com](https://uptimerobot.com) (free)
- Monitor: `https://ecomdash-api.onrender.com/health`
- Interval: 5 minutes
- Alert via email/Slack

**2. Error Tracking:**
If you set `SENTRY_DSN`, errors are automatically tracked at [sentry.io](https://sentry.io)

**3. Performance Monitoring:**
- View metrics at `https://ecomdash-api.onrender.com/metrics`
- Set up Grafana (optional, see full guide)

### Enable Auto-Deploy
Already enabled via `render.yaml`:
```yaml
autoDeploy: true
```

Every push to `main` branch triggers automatic deployment.

---

## Multi-Tenant Usage

### Generalized Backend (Each Store = Unique API Key)

EcomDash is designed for multi-tenant SaaS:

**Option 1: Shopify App (Recommended for Scale)**
- Single API key (yours)
- Per-store OAuth tokens (encrypted in database)
- One-click install for merchants
- Current implementation supports this

**Option 2: Custom App (Per-Store Credentials)**
Each merchant creates custom app in their Shopify store:
1. Merchant goes to Shopify Admin → Apps → Develop apps
2. Creates app with required scopes
3. Generates Admin API token
4. Provides token to your system:
   ```bash
   curl -X POST https://ecomdash-api.onrender.com/api/shops/register \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "merchant-store.myshopify.com",
       "admin_api_token": "shpat_...",
       "api_key": "optional",
       "api_secret": "optional"
     }'
   ```

### Tenant Isolation

Every database table includes `shop_id` foreign key:
```python
# All queries automatically filtered by shop
insights = await db.execute(
    select(Insight).where(Insight.shop_id == current_shop.id)
)
```

**Security:** Cascade delete on shop removal (GDPR compliance).

---

## Scaling

### Current Cost: $21/mo
- API: $7/mo (Starter)
- Worker: $7/mo (Starter)
- Database: $7/mo (Starter, 1GB)
- Redis: Free
- Frontend: Free

### When to Scale Up

**100-1,000 shops:**
```yaml
# Upgrade in Render Dashboard
API: Standard ($25/mo) with auto-scaling 1-3 instances
Worker: Standard ($25/mo)
Database: Standard ($20/mo, 10GB)
Redis: Starter ($10/mo)
Total: ~$80/mo
```

**1,000-10,000 shops:**
```yaml
API: Pro ($85/mo) with auto-scaling 3-10 instances
Worker: Pro ($85/mo) x2 instances
Database: Pro ($200/mo, 256GB)
Redis: Standard ($30/mo)
Total: ~$485/mo
```

Auto-scaling configured in `render.yaml`:
```yaml
scaling:
  minInstances: 1
  maxInstances: 10
  targetCPUPercent: 75
  targetMemoryPercent: 75
```

---

## Troubleshooting

### Build Fails
```bash
# Test locally
cd backend
docker build -t test .
```

### Database Connection Error
```bash
# Verify DATABASE_URL is set
render env list ecomdash-api | grep DATABASE_URL

# Test connection
render psql ecomdash-db -c "SELECT 1;"
```

### 503 Service Unavailable
```bash
# Check logs
render logs ecomdash-api --tail

# Common fix: Verify app listens on port 8000
# Dockerfile should have:
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Worker Not Processing Jobs
```bash
# Check worker logs
render logs ecomdash-worker --tail

# Verify Redis connection
render env list ecomdash-worker | grep REDIS_URL

# Restart worker
render deploy ecomdash-worker
```

### Shopify OAuth Fails
```bash
# Verify redirect URI matches exactly in Partners Dashboard
# Check SHOPIFY_APP_URL
render env list ecomdash-api | grep SHOPIFY_APP_URL
```

---

## Next Steps

1. **Read Full Guide:** See [RENDER_DEPLOYMENT_GUIDE.md](./RENDER_DEPLOYMENT_GUIDE.md) for comprehensive details
2. **Security Review:** Follow security best practices in Section 8
3. **Set Up CI/CD:** See Section 11 for GitHub Actions workflow
4. **Monitor:** Configure Sentry, Prometheus, and uptime monitoring
5. **Test:** Install on development store and verify all features
6. **Launch:** Deploy to production and monitor for 24-48 hours

---

## Support

- **Render Docs:** [render.com/docs](https://render.com/docs)
- **Render CLI:** [github.com/render-oss/cli](https://github.com/render-oss/cli)
- **Render Support:** support@render.com
- **Render Status:** [status.render.com](https://status.render.com)

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `render.yaml` | Infrastructure as Code |
| `backend/Dockerfile` | API container |
| `backend/Dockerfile.worker` | Worker container |
| `backend/.env.example` | Environment variables template |
| `backend/alembic/` | Database migrations |
| `RENDER_DEPLOYMENT_GUIDE.md` | Comprehensive guide (this is the summary) |

---

**Deployment Time:** ~30 minutes total
**Cost:** $21/mo (starter) → $80/mo (growth) → $485/mo (scale)
**Scalability:** Supports 1-10,000+ shops

Happy deploying! 🚀
