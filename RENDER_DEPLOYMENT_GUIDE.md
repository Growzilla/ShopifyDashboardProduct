# EcomDash V2 - Comprehensive Render Deployment Guide

**Version:** 2.0.0
**Last Updated:** 2026-01-09
**Target Platform:** Render.com
**Architecture:** Multi-tenant Shopify Analytics Platform

---

## Table of Contents

1. [Overview](#1-overview)
2. [Render Platform Architecture](#2-render-platform-architecture)
3. [Render CLI Setup & Capabilities](#3-render-cli-setup--capabilities)
4. [PostgreSQL Database Setup](#4-postgresql-database-setup)
5. [Environment Variables & Secrets Management](#5-environment-variables--secrets-management)
6. [Multi-Tenant Generalization Strategy](#6-multi-tenant-generalization-strategy)
7. [Custom App vs Shopify App Architecture](#7-custom-app-vs-shopify-app-architecture)
8. [Security Best Practices](#8-security-best-practices)
9. [Scaling & Cost Optimization](#9-scaling--cost-optimization)
10. [Monitoring & Observability](#10-monitoring--observability)
11. [CI/CD Pipeline](#11-cicd-pipeline)
12. [Step-by-Step Deployment Procedure](#12-step-by-step-deployment-procedure)
13. [Troubleshooting](#13-troubleshooting)
14. [Production Checklist](#14-production-checklist)

---

## 1. Overview

### System Architecture

EcomDash V2 is a **multi-tenant Shopify analytics platform** built with:

- **Backend:** FastAPI (Python 3.11+) with async/await
- **Database:** PostgreSQL 15+ with pgvector extension
- **Cache/Queue:** Redis for caching and ARQ job queue
- **Worker:** Background job processing with ARQ
- **Frontend:** React/Remix (static build)
- **Deployment:** Render.com with Docker containers

### Infrastructure as Code

The deployment uses Render Blueprints (`render.yaml`) for reproducible infrastructure:

```
EcomDash V2 Stack:
├── ecomdash-api (Web Service)      → FastAPI backend
├── ecomdash-worker (Worker)        → ARQ background jobs
├── ecomdash-frontend (Static)      → React admin UI
├── ecomdash-db (PostgreSQL)        → Primary database
└── ecomdash-redis (Redis)          → Cache + job queue
```

**Monthly Cost Estimate:** $21-35/mo
- API: $7/mo (Starter) → $25/mo (Standard for auto-scaling)
- Worker: $7/mo (Starter)
- Database: $7/mo (Starter, 1GB storage, 256MB RAM)
- Redis: Free (25MB)
- Frontend: Free (static hosting)

---

## 2. Render Platform Architecture

### Service Types

| Service Type | Purpose | Pricing | Use Case |
|--------------|---------|---------|----------|
| **Web Service** | HTTP server | $7-25/mo | API endpoints |
| **Worker** | Background jobs | $7/mo | ARQ queue processing |
| **Static Site** | CDN hosting | Free | Frontend SPA |
| **PostgreSQL** | Managed database | $7-450/mo | Persistent data |
| **Redis** | In-memory store | Free-$10/mo | Caching, queues |

### Regions

Render operates in multiple AWS regions:
- **Oregon (us-west-2)** - Recommended for US deployments
- **Ohio (us-east-2)** - Alternative US region
- **Frankfurt** - European deployments
- **Singapore** - Asia-Pacific deployments

**Best Practice:** Deploy all services in the same region to minimize latency and data transfer costs.

### Auto-Deploy Mechanism

Render monitors your GitHub/GitLab repository and triggers deployments when:
1. Code is pushed/merged to the specified branch
2. Blueprint (`render.yaml`) changes are detected
3. Manual deploy is triggered via Dashboard/CLI
4. Environment variables are updated (if configured)

**Deployment Flow:**
```
Git Push → GitHub → Render Webhook → Build Docker Image → Run Health Check → Route Traffic → Old Instance Shutdown
```

---

## 3. Render CLI Setup & Capabilities

### Installation

**macOS/Linux (Homebrew):**
```bash
brew install render
```

**Linux (Direct Download):**
```bash
curl -L https://github.com/render-oss/cli/releases/latest/download/cli_linux_amd64.tar.gz -o render.tar.gz
tar -xzf render.tar.gz
sudo mv render /usr/local/bin/
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://github.com/render-oss/cli/releases/latest/download/cli_windows_amd64.zip" -OutFile "render.zip"
Expand-Archive -Path "render.zip" -DestinationPath "$env:ProgramFiles\Render"
```

### Authentication

```bash
# Login (opens browser for token generation)
render login

# Verify authentication
render whoami
```

**Token Management:**
- CLI tokens periodically expire (~90 days)
- Re-authenticate with `render login` if commands fail
- Tokens stored in `~/.render/config.yaml`

### Essential CLI Commands

**Service Management:**
```bash
# List all services
render services list

# View service details
render services get <service-id>

# View service logs (live tail)
render logs <service-id> --tail

# SSH into running service
render shell <service-id>
```

**Deployment Operations:**
```bash
# Trigger manual deploy
render deploy <service-id>

# Deploy specific commit
render deploy <service-id> --commit <commit-hash>

# View deployment status
render deploys list <service-id>

# Cancel ongoing deployment
render deploy cancel <deployment-id>
```

**Database Operations:**
```bash
# List databases
render databases list

# Open psql shell
render psql <database-name>

# Execute SQL file
render psql <database-name> < migrations/schema.sql

# Create database backup
render backup create <database-id>

# List backups
render backups list <database-id>
```

**Environment Variables:**
```bash
# List environment variables
render env list <service-id>

# Set environment variable
render env set <service-id> KEY=value

# Bulk update from file
render env sync <service-id> --file .env.production
```

**Git Integration:**
```bash
# Connect service to Git repository
render repo connect <service-id> <repo-url>

# Update branch for auto-deploy
render repo set-branch <service-id> <branch-name>

# View connected repository
render repo info <service-id>
```

### Blueprint Management

**Important:** Render CLI does **not** have a direct `render blueprint apply` command. Blueprint deployment is handled through the Dashboard.

**Workflow:**
1. Create/update `render.yaml` in your repository
2. Commit and push to GitHub/GitLab
3. In Render Dashboard: **New → Blueprint**
4. Select repository and branch
5. Review proposed changes
6. Click **Apply**

**Blueprint Validation (Local):**
```bash
# Validate render.yaml syntax
yamllint render.yaml

# Or use Python
python -c "import yaml; yaml.safe_load(open('render.yaml'))"
```

### CLI-Based Deployment Workflow

**Full deployment with Git:**
```bash
# 1. Make code changes
vim backend/app/main.py

# 2. Commit changes
git add .
git commit -m "feat: add new analytics endpoint"

# 3. Push to trigger auto-deploy
git push origin main

# 4. Monitor deployment
render logs ecomdash-api --tail
```

**Manual deploy without Git push:**
```bash
# Trigger deploy from current HEAD
render deploy ecomdash-api

# Deploy specific commit
render deploy ecomdash-api --commit abc123def456
```

---

## 4. PostgreSQL Database Setup

### Database Configuration

**Render PostgreSQL Features:**
- Automatic backups (daily for Starter plan, hourly for higher tiers)
- SSL/TLS encryption in transit
- Connection pooling built-in
- pgvector extension support (for embeddings)
- Read replicas (Standard plan and above)

**Database Specifications (Starter Plan - $7/mo):**
- **RAM:** 256 MB
- **Storage:** 1 GB SSD
- **Connections:** 25 concurrent
- **Backups:** Daily (7-day retention)
- **Region:** Same as services

### Creating Database via Blueprint

Your existing `render.yaml` already includes database configuration:

```yaml
databases:
  - name: ecomdash-db
    databaseName: ecomdash
    user: ecomdash
    region: oregon
    plan: starter
    ipAllowList: []  # Allow from all Render services
```

**Connection String Format:**
```
postgresql://ecomdash:<password>@dpg-<id>.oregon-postgres.render.com/ecomdash
```

### Database Initialization

**1. Enable Extensions:**
```bash
# Connect via CLI
render psql ecomdash-db

# Enable pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

# Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

# Verify extensions
\dx
```

**2. Run Alembic Migrations:**

Your backend uses Alembic for schema management. Run migrations during first deployment:

```bash
# SSH into API service
render shell ecomdash-api

# Run migrations
cd /app
alembic upgrade head

# Verify tables
alembic current
```

**Pre-Deploy Hook (Recommended):**

Add to `render.yaml` for automatic migrations:

```yaml
services:
  - type: web
    name: ecomdash-api
    runtime: docker
    dockerfilePath: ./backend/Dockerfile
    dockerContext: ./backend
    preDeployCommand: "alembic upgrade head"  # Run migrations before deploy
    # ... rest of config
```

### Migration Management

**Create New Migration:**
```bash
# Locally, with database connection
cd backend
alembic revision --autogenerate -m "add_new_column"

# Review generated migration
cat alembic/versions/<timestamp>_add_new_column.py

# Commit and push
git add alembic/versions/
git commit -m "db: add new column migration"
git push
```

**Migration Best Practices:**
1. **Always review autogenerated migrations** - Alembic can miss complex changes
2. **Test migrations on staging first** - Use separate Render environment
3. **Backup before major migrations:**
   ```bash
   render backup create ecomdash-db
   ```
4. **Zero-downtime migrations:**
   - Add columns as nullable first
   - Backfill data in background job
   - Add NOT NULL constraint in subsequent migration
5. **Rollback capability:**
   ```bash
   alembic downgrade -1  # Rollback one migration
   ```

### Connection Pooling

**SQLAlchemy Configuration (already in your code):**

`backend/app/core/database.py`:
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=20,              # Connection pool size
    max_overflow=10,           # Additional connections under load
    pool_pre_ping=True,        # Verify connection before use
    pool_recycle=3600,         # Recycle connections after 1 hour
)
```

**Render PostgreSQL Limits:**
- **Starter:** 25 concurrent connections
- **Standard:** 120 concurrent connections
- **Pro:** 300 concurrent connections

**Scaling Strategy:**
- If hitting connection limits with multiple services, use **PgBouncer** (external connection pooler)
- Or upgrade to Standard plan ($20/mo) for 120 connections

### Database Monitoring

```bash
# Connection stats
render psql ecomdash-db -c "SELECT count(*) FROM pg_stat_activity WHERE datname='ecomdash';"

# Database size
render psql ecomdash-db -c "SELECT pg_size_pretty(pg_database_size('ecomdash'));"

# Table sizes
render psql ecomdash-db -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Slow queries
render psql ecomdash-db -c "SELECT query, calls, total_exec_time, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

---

## 5. Environment Variables & Secrets Management

### Environment Variable Types

Render supports three types of environment variables:

| Type | Description | Use Case |
|------|-------------|----------|
| **Manual** | Set via Dashboard/CLI | API keys, secrets |
| **Generated** | Auto-generated by Render | SECRET_KEY, ENCRYPTION_KEY |
| **Linked** | Reference other resources | DATABASE_URL from database |

### Required Environment Variables

**Application Settings:**
```bash
APP_NAME=EcomDash V2 API
APP_VERSION=2.0.0
DEBUG=false                          # Always false in production
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000                            # Render requires 8000 or 10000
LOG_LEVEL=INFO
```

**Database Connection:**
```bash
# Auto-linked from ecomdash-db
DATABASE_URL=postgresql://...       # fromDatabase in render.yaml
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=false                  # Disable SQL logging in production
```

**Redis Connection:**
```bash
# Auto-linked from ecomdash-redis
REDIS_URL=redis://...               # fromService in render.yaml
```

**Security (Auto-Generated):**
```bash
SECRET_KEY=<auto-generated-by-render>
ENCRYPTION_KEY=<auto-generated-by-render>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

**CORS Configuration:**
```bash
# Comma-separated list
ALLOWED_ORIGINS=https://admin.shopify.com,https://ecomdash.onrender.com,https://ecomdash-frontend.onrender.com
```

**Shopify Configuration (Manual - Required):**
```bash
SHOPIFY_API_KEY=<from_shopify_partners_dashboard>
SHOPIFY_API_SECRET=<from_shopify_partners_dashboard>
SHOPIFY_SCOPES=read_products,read_orders,read_customers,read_inventory,read_discounts
SHOPIFY_APP_URL=https://ecomdash-api.onrender.com
```

**AI/ML (Manual - Required):**
```bash
OPENAI_API_KEY=sk-<your_openai_api_key>
OPENAI_MODEL=gpt-4-turbo-preview
```

**Notifications (Manual - Optional):**
```bash
RESEND_API_KEY=re_<your_resend_api_key>
APP_URL=https://ecomdash.onrender.com
```

**Observability (Manual - Optional):**
```bash
SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project>
ENABLE_METRICS=true
```

### Setting Environment Variables

**Via Render Dashboard:**
1. Open service (e.g., `ecomdash-api`)
2. Navigate to **Environment** tab
3. Click **Add Environment Variable**
4. Enter key-value pairs
5. Click **Save Changes** (triggers redeploy)

**Via Render CLI:**
```bash
# Single variable
render env set ecomdash-api SHOPIFY_API_KEY=abc123

# Multiple variables
render env set ecomdash-api \
  SHOPIFY_API_KEY=abc123 \
  SHOPIFY_API_SECRET=def456 \
  OPENAI_API_KEY=sk-ghi789
```

**Bulk Import from File:**
```bash
# Create .env.production (never commit this!)
cat > .env.production <<EOF
SHOPIFY_API_KEY=abc123
SHOPIFY_API_SECRET=def456
OPENAI_API_KEY=sk-ghi789
RESEND_API_KEY=re-jkl012
SENTRY_DSN=https://...
EOF

# Sync to Render (not officially supported, use script)
while IFS='=' read -r key value; do
  render env set ecomdash-api "$key=$value"
done < .env.production
```

### Environment Variable Groups

Your `render.yaml` includes an environment group for shared secrets:

```yaml
envVarGroups:
  - name: ecomdash-secrets
    envVars:
      - key: SHOPIFY_API_KEY
        sync: false
      - key: SHOPIFY_API_SECRET
        sync: false
      - key: OPENAI_API_KEY
        sync: false
      - key: RESEND_API_KEY
        sync: false
      - key: SENTRY_DSN
        sync: false
```

**Using Environment Groups:**
1. Create group in Dashboard: **Environment → Environment Groups → New**
2. Add variables to group
3. Link group to services (automatically linked via Blueprint)

**Benefits:**
- Share secrets across multiple services
- Update once, apply to all linked services
- Better organization and auditability

### Secrets Rotation

**Best Practice Schedule:**
- **SECRET_KEY / ENCRYPTION_KEY:** Every 90 days
- **SHOPIFY_API_SECRET:** When leaked or annually
- **OPENAI_API_KEY:** When leaked or bi-annually
- **Database passwords:** Managed by Render, rotated automatically

**Rotation Procedure:**
```bash
# 1. Generate new secret
new_secret=$(openssl rand -base64 32)

# 2. Update environment variable
render env set ecomdash-api NEW_SECRET_KEY=$new_secret

# 3. Deploy with both old and new keys (dual-key validation)
# 4. Wait 24 hours for all sessions to cycle
# 5. Remove old key
```

### Security Best Practices

1. **Never commit secrets to Git:**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   echo ".env.*" >> .gitignore
   echo "!.env.example" >> .gitignore
   ```

2. **Use `sync: false` for all secrets** in `render.yaml` to prevent auto-sync conflicts

3. **Encrypt sensitive data at rest** using `ENCRYPTION_KEY` (Fernet cipher in your code)

4. **Audit access:**
   ```bash
   # View who has access to environment variables
   # (Available in Render Dashboard → Team Settings)
   ```

5. **Use different secrets per environment:**
   - Development: Local `.env` file
   - Staging: Separate Render environment
   - Production: Production Render environment

---

## 6. Multi-Tenant Generalization Strategy

### Architecture Overview

EcomDash V2 implements **shared database multi-tenancy** where:
- **Single API deployment** serves all Shopify stores
- **Single database** with `shop_id` isolation
- **Per-shop OAuth tokens** encrypted and stored in `shops` table
- **Tenant context** extracted from API requests

### Database Schema Design

**Core Tenant Model:**

`backend/app/models/shop.py`:
```python
class Shop(Base):
    __tablename__ = "shops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String, unique=True, nullable=False, index=True)  # e.g., "store.myshopify.com"
    access_token_encrypted = Column(Text, nullable=False)  # Fernet encrypted
    scopes = Column(String, nullable=False)  # OAuth scopes
    settings = Column(JSON, default={})  # Per-shop configuration

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_sync_at = Column(DateTime(timezone=True))
    sync_status = Column(String, default="pending")

    # Relationships (cascading delete for data isolation)
    products = relationship("Product", back_populates="shop", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="shop", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="shop", cascade="all, delete-orphan")
```

**Child Tables (All Reference shop_id):**
```python
class Product(Base):
    __tablename__ = "products"
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"))
    # ... other fields

class Order(Base):
    __tablename__ = "orders"
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"))
    # ... other fields

class Insight(Base):
    __tablename__ = "insights"
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"))
    # ... other fields
```

**Indexes for Performance:**
```sql
-- Composite indexes for time-series queries
CREATE INDEX idx_products_shop_created ON products(shop_id, created_at DESC);
CREATE INDEX idx_orders_shop_date ON orders(shop_id, processed_at DESC);
CREATE INDEX idx_insights_shop_date ON insights(shop_id, created_at DESC);

-- Unique constraint for tenant isolation
CREATE UNIQUE INDEX idx_shops_domain ON shops(domain);
```

### API Request Context

**1. Shop Identification Methods:**

**Option A: Query Parameter (Current Implementation):**
```python
@router.get("/api/insights")
async def list_insights(
    shop_domain: str = Query(..., description="Shopify store domain"),
    db: AsyncSession = Depends(get_db)
):
    # Validate shop exists
    shop = await shop_repo.get_by_domain(db, shop_domain)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    # Query with shop_id filter
    insights = await db.execute(
        select(Insight).where(Insight.shop_id == shop.id)
    )
    return insights.scalars().all()
```

**Option B: Subdomain (Recommended for Scale):**
```python
# shopA.ecomdash.com → shop_id: uuid-A
# shopB.ecomdash.com → shop_id: uuid-B

@router.get("/api/insights")
async def list_insights(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Extract subdomain
    host = request.headers.get("host")
    subdomain = host.split('.')[0]  # e.g., "shopA"

    # Map subdomain to shop
    shop = await shop_repo.get_by_subdomain(db, subdomain)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    # Continue with shop.id
```

**Option C: JWT Token (Most Secure):**
```python
@router.get("/api/insights")
async def list_insights(
    current_shop: Shop = Depends(get_current_shop),  # From JWT
    db: AsyncSession = Depends(get_db)
):
    insights = await db.execute(
        select(Insight).where(Insight.shop_id == current_shop.id)
    )
    return insights.scalars().all()
```

**2. Dependency Injection for Tenant Context:**

`backend/app/core/dependencies.py`:
```python
async def get_current_shop(
    shop_domain: str = Query(..., alias="shop"),
    db: AsyncSession = Depends(get_db)
) -> Shop:
    """Extract and validate shop from request."""
    shop = await db.scalar(
        select(Shop).where(Shop.domain == shop_domain)
    )
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    return shop

# Use in all endpoints
@router.get("/api/dashboard/stats")
async def get_dashboard_stats(
    shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_db)
):
    # shop is guaranteed to exist and validated
    return await dashboard_service.compute_stats(db, shop.id)
```

### Shopify OAuth Flow (Multi-Tenant)

**1. Installation Flow:**

```
┌─────────────┐                           ┌──────────────┐
│  Merchant   │                           │   Shopify    │
│ (Store A)   │                           │              │
└──────┬──────┘                           └──────┬───────┘
       │ 1. Install App                          │
       ├────────────────────────────────────────>│
       │                                          │
       │ 2. Redirect to OAuth                    │
       │<────────────────────────────────────────┤
       │                                          │
       │ 3. Approve scopes                       │
       ├────────────────────────────────────────>│
       │                                          │
       │ 4. Callback with code                   │
       │<────────────────────────────────────────┤
       ▼                                          │
┌──────────────────┐                             │
│  EcomDash API    │                             │
│  /auth/callback  │ 5. Exchange code for token  │
│                  ├────────────────────────────>│
│                  │<────────────────────────────┤
│                  │ 6. Access token             │
│                  │                             │
│  POST /api/shops │ 7. Store encrypted token    │
│                  │                             │
│  shop_id: uuid-A │                             │
│  domain: storeA  │                             │
│  token: encrypted│                             │
└──────────────────┘                             │
```

**2. Token Storage:**

`backend/app/routers/shops.py`:
```python
from app.core.security import encrypt_token

@router.post("/api/shops", response_model=ShopResponse)
async def create_shop(
    shop_data: ShopCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if shop already exists
    existing_shop = await db.scalar(
        select(Shop).where(Shop.domain == shop_data.domain)
    )

    if existing_shop:
        # Update token (reinstall scenario)
        existing_shop.access_token_encrypted = encrypt_token(shop_data.accessToken)
        existing_shop.scopes = shop_data.scopes
        await db.commit()
        return existing_shop

    # Create new shop
    shop = Shop(
        domain=shop_data.domain,
        access_token_encrypted=encrypt_token(shop_data.accessToken),
        scopes=shop_data.scopes,
    )
    db.add(shop)
    await db.commit()
    await db.refresh(shop)

    return shop
```

### Unique API Key per Shop

**Current Implementation:**
- **Single SHOPIFY_API_KEY** for entire platform (Shopify app credentials)
- **Per-shop access tokens** (OAuth tokens) stored encrypted in database

**For Custom App (Non-Shopify App Store):**

If you want **each merchant to use their own Shopify custom app credentials**:

```python
# Modified Shop model
class Shop(Base):
    __tablename__ = "shops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String, unique=True, nullable=False)

    # Option 1: Custom app credentials (per merchant)
    api_key = Column(String, nullable=True)  # Their custom app API key
    api_secret_encrypted = Column(Text, nullable=True)  # Encrypted
    access_token_encrypted = Column(Text, nullable=False)  # Admin API token

    # OR Option 2: Admin API token only (simpler)
    # Merchant creates custom app in their store, provides admin API token
    admin_api_token_encrypted = Column(Text, nullable=False)

    scopes = Column(String, nullable=False)
    # ... rest of fields
```

**API Client Usage:**

`backend/app/services/shopify_client.py`:
```python
class ShopifyGraphQLClient:
    def __init__(self, shop: Shop):
        # Decrypt shop-specific token
        self.access_token = decrypt_token(shop.access_token_encrypted)
        self.shop_domain = shop.domain

        # Optionally use shop-specific API key if available
        if shop.api_key:
            self.api_key = shop.api_key
            self.api_secret = decrypt_token(shop.api_secret_encrypted)
        else:
            # Fall back to platform-wide credentials
            self.api_key = settings.SHOPIFY_API_KEY
            self.api_secret = settings.SHOPIFY_API_SECRET

        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }
        self.graphql_url = f"https://{shop.domain}/admin/api/2024-01/graphql.json"
```

### Data Isolation Verification

**Testing Tenant Isolation:**

`backend/tests/test_multi_tenancy.py`:
```python
import pytest
from app.models import Shop, Product, Insight

@pytest.mark.asyncio
async def test_shop_data_isolation(db_session):
    # Create two shops
    shop_a = Shop(domain="shopA.myshopify.com", ...)
    shop_b = Shop(domain="shopB.myshopify.com", ...)
    db_session.add_all([shop_a, shop_b])
    await db_session.commit()

    # Create products for each shop
    product_a = Product(shop_id=shop_a.id, title="Product A")
    product_b = Product(shop_id=shop_b.id, title="Product B")
    db_session.add_all([product_a, product_b])
    await db_session.commit()

    # Query shop A's products
    products_a = await db_session.scalars(
        select(Product).where(Product.shop_id == shop_a.id)
    )
    products_a = products_a.all()

    # Verify isolation
    assert len(products_a) == 1
    assert products_a[0].title == "Product A"
    assert all(p.shop_id == shop_a.id for p in products_a)
```

**Row-Level Security (Advanced):**

For extra safety, enable PostgreSQL Row-Level Security:

```sql
-- Enable RLS on products table
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

-- Create policy (requires application role)
CREATE POLICY products_isolation ON products
    FOR ALL
    TO ecomdash_api_role
    USING (shop_id = current_setting('app.current_shop_id')::uuid);

-- Set shop context in application
SET app.current_shop_id = 'uuid-here';
```

### Scaling Considerations

**Single Database Limits:**
- **Up to 10,000 shops:** Shared database with proper indexing
- **10,000-100,000 shops:** Consider sharding by shop_id range or region
- **100,000+ shops:** Database per shop or horizontally partitioned tables

**Sharding Strategy (If Needed):**

```python
# Hash shop_id to determine database shard
def get_shard_for_shop(shop_id: UUID) -> int:
    return hash(shop_id) % NUM_SHARDS

# Database URL selection
def get_database_url(shop_id: UUID) -> str:
    shard = get_shard_for_shop(shop_id)
    return f"postgresql://user:pass@db-shard-{shard}.render.com/ecomdash"
```

---

## 7. Custom App vs Shopify App Architecture

### Comparison Matrix

| Feature | **Custom App** | **Shopify App Store App** |
|---------|----------------|---------------------------|
| **Distribution** | Private (single store) | Public or Private (multiple stores) |
| **OAuth Flow** | Not required | Required (Shopify OAuth) |
| **Token Management** | Admin API token (manual) | Access token (OAuth) |
| **Installation** | Manual (via Shopify Admin) | One-click install (App Store) |
| **Scopes** | All scopes (Admin API) | Requested during OAuth |
| **API Key** | Per-store (unique) | Single app credentials |
| **Billing** | Not supported | Shopify App Billing API |
| **App Bridge** | Not supported | Full support |
| **Multi-Tenant** | One deployment per store | One deployment, many stores |
| **Webhooks** | Manual registration | Automatic registration |
| **Updates** | Manual per store | Automatic for all installs |
| **Uninstall** | Manual deletion | Webhook notification |
| **Use Case** | Internal tools, agency clients | SaaS products, scalability |

### Custom App Architecture (Current Codebase Path)

**Scenario:** You want each merchant to deploy their own EcomDash instance or provide their own API credentials.

**Architecture:**

```
Merchant A                    Merchant B                    Merchant C
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│ Shopify Store│             │ Shopify Store│             │ Shopify Store│
│              │             │              │             │              │
│ Custom App:  │             │ Custom App:  │             │ Custom App:  │
│ - API Key A  │             │ - API Key B  │             │ - API Key C  │
│ - Token A    │             │ - Token B    │             │ - Token C    │
└──────┬───────┘             └──────┬───────┘             └──────┬───────┘
       │                            │                            │
       │ HTTPS (Admin API)          │ HTTPS (Admin API)          │ HTTPS (Admin API)
       │                            │                            │
       ▼                            ▼                            ▼
┌───────────────────────────────────────────────────────────────────────┐
│               EcomDash Backend (Single Deployment)                    │
│                                                                       │
│  Shop Model:                                                          │
│  ├─ Shop A (domain, api_key_a, token_a_encrypted)                    │
│  ├─ Shop B (domain, api_key_b, token_b_encrypted)                    │
│  └─ Shop C (domain, api_key_c, token_c_encrypted)                    │
│                                                                       │
│  Generalized Backend: Uses shop-specific credentials per request     │
└───────────────────────────────────────────────────────────────────────┘
```

**Implementation:**

1. **Merchant creates custom app:**
   - Go to Shopify Admin → Apps → **App and sales channel settings**
   - Click **Develop apps** → **Create an app**
   - Configure Admin API scopes: `read_products`, `read_orders`, etc.
   - Install app → Generate Admin API access token

2. **Merchant provides credentials to EcomDash:**
   - Via registration form or API call:
   ```bash
   POST /api/shops/register
   {
     "domain": "merchantA.myshopify.com",
     "admin_api_token": "shpat_abc123...",
     "api_key": "optional-if-needed",
     "api_secret": "optional-if-needed"
   }
   ```

3. **Backend stores encrypted credentials:**
   ```python
   @router.post("/api/shops/register")
   async def register_shop(
       shop_data: ShopRegisterRequest,
       db: AsyncSession = Depends(get_db)
   ):
       shop = Shop(
           domain=shop_data.domain,
           access_token_encrypted=encrypt_token(shop_data.admin_api_token),
           # Optionally store API key/secret if needed
           api_key=shop_data.api_key,
           api_secret_encrypted=encrypt_token(shop_data.api_secret) if shop_data.api_secret else None,
       )
       db.add(shop)
       await db.commit()
       return {"status": "success", "shop_id": str(shop.id)}
   ```

4. **API client uses shop-specific credentials:**
   ```python
   client = ShopifyGraphQLClient(shop=shop)
   products = await client.get_products()
   ```

**Pros:**
- **Maximum control:** Each merchant controls their own credentials
- **No app review:** Skip Shopify App Store approval process
- **Custom scopes:** Each merchant can grant different scopes
- **Privacy:** No centralized OAuth token storage (merchant owns token)

**Cons:**
- **Manual setup:** Each merchant must create custom app
- **No billing integration:** Can't use Shopify App Billing API
- **Harder updates:** Must coordinate updates with all merchants
- **No App Bridge:** Can't embed in Shopify Admin UI

### Shopify App Store App Architecture (Recommended for SaaS)

**Scenario:** You want to distribute EcomDash as a public Shopify app for any merchant to install.

**Architecture:**

```
                     Shopify App Store
                           │
                           │ Merchant installs app
                           ▼
┌────────────────────────────────────────────────────────────┐
│              Shopify OAuth & App Bridge                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Store A  │  │ Store B  │  │ Store C  │  │ Store N  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │             │             │          │
│       └─────────────┴─────────────┴─────────────┘          │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            │
                            │ OAuth tokens (per store)
                            ▼
┌───────────────────────────────────────────────────────────┐
│              EcomDash Backend (Single Deployment)         │
│                                                           │
│  SHOPIFY_API_KEY:    abc123 (platform-wide)              │
│  SHOPIFY_API_SECRET: def456 (platform-wide)              │
│                                                           │
│  Shop Model:                                              │
│  ├─ Shop A (domain, access_token_encrypted, scopes)      │
│  ├─ Shop B (domain, access_token_encrypted, scopes)      │
│  └─ Shop C (domain, access_token_encrypted, scopes)      │
│                                                           │
│  OAuth Flow: Centralized (auth-proxy service)            │
└───────────────────────────────────────────────────────────┘
```

**Implementation:**

1. **Create Shopify Partners account:**
   - Visit [partners.shopify.com](https://partners.shopify.com)
   - Create partner account

2. **Create app in Partners Dashboard:**
   - Go to **Apps** → **Create app**
   - Choose **Public app** or **Custom app**
   - Configure:
     - **App URL:** `https://ecomdash-api.onrender.com`
     - **Allowed redirection URL(s):**
       ```
       https://ecomdash-api.onrender.com/auth/callback
       https://ecomdash-frontend.onrender.com/auth/callback
       ```
     - **Scopes:** Select required scopes
   - Get **API key** and **API secret**

3. **Add OAuth endpoints to your backend:**

   Your reference codebase already has this pattern in `/home/ghostking/projects/ecomapps/ecomdash/apps/auth-proxy/src/server.ts`.

   Adapt for your FastAPI backend:

   `backend/app/routers/auth.py`:
   ```python
   from fastapi import APIRouter, Request, HTTPException
   from fastapi.responses import RedirectResponse
   import httpx

   router = APIRouter()

   @router.get("/auth")
   async def initiate_oauth(shop: str):
       """Initiate Shopify OAuth flow."""
       scopes = settings.SHOPIFY_SCOPES
       redirect_uri = f"{settings.SHOPIFY_APP_URL}/auth/callback"

       oauth_url = (
           f"https://{shop}/admin/oauth/authorize?"
           f"client_id={settings.SHOPIFY_API_KEY}&"
           f"scope={scopes}&"
           f"redirect_uri={redirect_uri}&"
           f"state={generate_nonce()}"
       )
       return RedirectResponse(oauth_url)

   @router.get("/auth/callback")
   async def oauth_callback(
       code: str,
       shop: str,
       state: str,
       db: AsyncSession = Depends(get_db)
   ):
       """Handle OAuth callback and store token."""
       # Verify state (CSRF protection)
       if not verify_nonce(state):
           raise HTTPException(status_code=400, detail="Invalid state")

       # Exchange code for access token
       token_url = f"https://{shop}/admin/oauth/access_token"
       async with httpx.AsyncClient() as client:
           response = await client.post(token_url, json={
               "client_id": settings.SHOPIFY_API_KEY,
               "client_secret": settings.SHOPIFY_API_SECRET,
               "code": code,
           })
           response.raise_for_status()
           data = response.json()

       # Store shop and token
       access_token = data["access_token"]
       scopes = data["scope"]

       shop_obj = await db.scalar(select(Shop).where(Shop.domain == shop))
       if shop_obj:
           # Update existing
           shop_obj.access_token_encrypted = encrypt_token(access_token)
           shop_obj.scopes = scopes
       else:
           # Create new
           shop_obj = Shop(
               domain=shop,
               access_token_encrypted=encrypt_token(access_token),
               scopes=scopes,
           )
           db.add(shop_obj)

       await db.commit()

       # Redirect to app frontend
       frontend_url = f"{settings.FRONTEND_URL}?shop={shop}&token={generate_jwt(shop_obj)}"
       return RedirectResponse(frontend_url)
   ```

4. **Register webhooks after installation:**

   `backend/app/services/webhook_manager.py`:
   ```python
   async def register_webhooks(shop: Shop):
       """Register mandatory webhooks after installation."""
       client = ShopifyGraphQLClient(shop)

       webhooks = [
           {"topic": "app/uninstalled", "address": f"{settings.SHOPIFY_APP_URL}/webhooks/app_uninstalled"},
           {"topic": "shop/redact", "address": f"{settings.SHOPIFY_APP_URL}/webhooks/shop_redact"},
           {"topic": "customers/data_request", "address": f"{settings.SHOPIFY_APP_URL}/webhooks/customer_data_request"},
           {"topic": "customers/redact", "address": f"{settings.SHOPIFY_APP_URL}/webhooks/customer_redact"},
       ]

       for webhook in webhooks:
           await client.execute_query(
               mutation="""
               mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
                 webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
                   webhookSubscription {
                     id
                   }
                 }
               }
               """,
               variables={
                   "topic": webhook["topic"],
                   "webhookSubscription": {
                       "callbackUrl": webhook["address"],
                       "format": "JSON"
                   }
               }
           )
   ```

5. **Handle webhooks:**

   `backend/app/routers/webhooks.py`:
   ```python
   from app.core.security import verify_shopify_hmac

   @router.post("/webhooks/app_uninstalled")
   async def handle_app_uninstalled(
       request: Request,
       db: AsyncSession = Depends(get_db)
   ):
       # Verify HMAC
       body = await request.body()
       hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")
       if not verify_shopify_hmac(hmac_header, body):
           raise HTTPException(status_code=401, detail="Invalid HMAC")

       # Parse webhook
       data = await request.json()
       shop_domain = data.get("domain")

       # Delete shop and cascade all data
       shop = await db.scalar(select(Shop).where(Shop.domain == shop_domain))
       if shop:
           await db.delete(shop)
           await db.commit()

       return {"status": "success"}
   ```

**Pros:**
- **One-click install:** Merchants install from App Store
- **Automatic updates:** Update once, applies to all stores
- **Billing integration:** Use Shopify App Billing API
- **App Bridge:** Embed in Shopify Admin UI
- **Webhooks:** Automatic registration and handling
- **Scalability:** Designed for thousands of stores

**Cons:**
- **App review:** Must pass Shopify App Store review
- **Centralized credentials:** You manage all OAuth tokens
- **Scopes:** Must request all scopes upfront
- **Compliance:** GDPR webhooks mandatory (48-hour response time)

### Recommendation

**For EcomDash V2:**

**Use Shopify App Store App Architecture** because:
1. Your existing `render.yaml` already supports multi-tenant SaaS model
2. Your `Shop` model is designed for OAuth token storage
3. You have single `SHOPIFY_API_KEY` environment variable (platform-wide)
4. Reference codebase at `/home/ghostking/projects/ecomapps/ecomdash` uses this pattern
5. Scalability: Support thousands of stores without per-store configuration

**If you need to start quickly without App Store approval:**
- Use **Custom App** initially for beta testing with limited merchants
- Migrate to **Shopify App** once ready for public launch
- Backend code supports both patterns with minimal changes

---

## 8. Security Best Practices

### Token Encryption

**Current Implementation (Fernet Symmetric Encryption):**

`backend/app/core/security.py`:
```python
from cryptography.fernet import Fernet
import hashlib
import base64

def get_fernet_key() -> bytes:
    """Derive Fernet key from ENCRYPTION_KEY."""
    key = settings.ENCRYPTION_KEY.encode()
    hash_key = hashlib.sha256(key).digest()
    return base64.urlsafe_b64encode(hash_key)

def encrypt_token(token: str) -> str:
    """Encrypt access token using Fernet."""
    fernet = Fernet(get_fernet_key())
    encrypted = fernet.encrypt(token.encode())
    return encrypted.decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt access token."""
    fernet = Fernet(get_fernet_key())
    decrypted = fernet.decrypt(encrypted_token.encode())
    return decrypted.decode()
```

**Best Practices:**
1. **Use auto-generated ENCRYPTION_KEY** in Render (32+ characters)
2. **Never log decrypted tokens:**
   ```python
   # Bad
   logger.info(f"Using token: {decrypted_token}")

   # Good
   logger.info(f"Using token for shop: {shop.domain}")
   ```
3. **Rotate encryption keys periodically:**
   - Support dual-key decryption during rotation
   - Re-encrypt all tokens with new key
4. **Use separate keys per environment:**
   - Development: Local `.env`
   - Staging: Separate Render environment
   - Production: Production Render environment

### HTTPS/TLS

**Render provides automatic TLS:**
- Free SSL certificates via Let's Encrypt
- Auto-renewal before expiration
- TLS 1.2 and 1.3 support
- HTTPS enforced by default

**Configuration:**
- No manual SSL setup required
- Custom domains supported (add in Dashboard)
- Redirect HTTP → HTTPS automatic

### CORS Configuration

**Current Implementation:**

`backend/app/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),  # Explicit list
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Shopify-Access-Token",
        "X-Request-ID",
    ],
)
```

**Production CORS:**
```bash
# In Render environment variables
ALLOWED_ORIGINS=https://admin.shopify.com,https://ecomdash-frontend.onrender.com
```

**DO NOT USE:**
```python
# NEVER in production
allow_origins=["*"]  # Security risk!
```

### Rate Limiting

**Application-Level Rate Limiting:**

Install middleware:
```bash
pip install slowapi
```

`backend/app/middleware/rate_limit.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Apply to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Use on endpoints
@router.post("/api/insights")
@limiter.limit("100/minute")
async def create_insight(request: Request):
    ...
```

**Shopify API Rate Limiting:**

Your existing `shopify_client.py` already handles this:
```python
class ShopifyGraphQLClient:
    MAX_RETRIES = 3
    RATE_LIMIT_DELAY = 0.5  # 500ms between calls

    async def execute_query(self, query: str, variables: dict):
        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.graphql_url,
                        json={"query": query, "variables": variables},
                        headers=self.headers,
                        timeout=30.0
                    )

                    # Check rate limit headers
                    call_limit = response.headers.get("X-Shopify-Shop-Api-Call-Limit")
                    # Format: "10/40" (10 calls used, 40 max)

                    if response.status_code == 429:
                        # Rate limited, exponential backoff
                        await asyncio.sleep(2 ** attempt)
                        continue

                    # Respect rate limit
                    await asyncio.sleep(self.RATE_LIMIT_DELAY)
                    return response.json()
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
```

### Webhook HMAC Verification

**Implementation:**

`backend/app/core/security.py`:
```python
import hmac
import hashlib
import base64

def verify_shopify_hmac(hmac_header: str, body: bytes) -> bool:
    """Verify webhook HMAC signature."""
    secret = settings.SHOPIFY_API_SECRET.encode()
    computed_hmac = base64.b64encode(
        hmac.new(secret, body, hashlib.sha256).digest()
    ).decode()

    # Constant-time comparison
    return hmac.compare_digest(computed_hmac, hmac_header)
```

**Usage:**
```python
@router.post("/webhooks/app_uninstalled")
async def handle_webhook(request: Request):
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")

    if not verify_shopify_hmac(hmac_header, body):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

    # Process webhook
    ...
```

### Input Validation

**Use Pydantic for all inputs:**

```python
from pydantic import BaseModel, Field, validator

class ShopCreate(BaseModel):
    domain: str = Field(..., regex=r'^[a-z0-9-]+\.myshopify\.com$')
    accessToken: str = Field(..., min_length=32)
    scopes: str

    @validator('domain')
    def validate_domain(cls, v):
        if not v.endswith('.myshopify.com'):
            raise ValueError('Invalid Shopify domain')
        return v.lower()

@router.post("/api/shops")
async def create_shop(shop_data: ShopCreate):
    # shop_data is already validated
    ...
```

### SQL Injection Prevention

**SQLAlchemy ORM protects against SQL injection:**

```python
# Safe (parameterized)
result = await db.execute(
    select(Shop).where(Shop.domain == user_input)
)

# NEVER do this (vulnerable)
query = f"SELECT * FROM shops WHERE domain = '{user_input}'"
await db.execute(text(query))
```

### Environment Variable Security

1. **Never commit secrets to Git:**
   ```bash
   # .gitignore
   .env
   .env.*
   !.env.example
   ```

2. **Use Render's secret management:**
   - Set `sync: false` in `render.yaml`
   - Manually set via Dashboard or CLI

3. **Audit access:**
   - Limit team members with access to production environment
   - Use Render's team roles

4. **Rotate secrets regularly:**
   - SECRET_KEY: Every 90 days
   - ENCRYPTION_KEY: Every 90 days
   - Database password: Managed by Render

### Logging & Audit Trail

**Structured Logging (Already Implemented):**

`backend/app/core/logging.py`:
```python
import structlog

logger = structlog.get_logger()

# Usage in code
logger.info(
    "shop_registered",
    shop_id=str(shop.id),
    domain=shop.domain,
    scopes=shop.scopes,
)

# Production output (JSON)
{"event": "shop_registered", "shop_id": "uuid...", "domain": "...", "timestamp": "..."}
```

**Sensitive Data Redaction:**
```python
# Never log tokens
logger.info("shopify_api_call", shop_domain=shop.domain)  # Good

# Bad
logger.info("shopify_api_call", access_token=token)  # Never do this
```

### Compliance (GDPR)

**Mandatory Shopify Webhooks:**

1. **customers/data_request** - Respond within 48 hours with customer data export
2. **customers/redact** - Delete customer data within 30 days
3. **shop/redact** - Delete all shop data within 48 hours after uninstall

**Implementation:**

`backend/app/routers/webhooks.py`:
```python
@router.post("/webhooks/shop_redact")
async def handle_shop_redact(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # Verify HMAC
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")
    if not verify_shopify_hmac(hmac_header, body):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

    data = await request.json()
    shop_domain = data.get("shop_domain")

    # Delete shop (cascades to all related data)
    shop = await db.scalar(select(Shop).where(Shop.domain == shop_domain))
    if shop:
        await db.delete(shop)
        await db.commit()

        # Log for audit
        logger.info(
            "shop_redacted",
            shop_id=str(shop.id),
            shop_domain=shop_domain,
            reason="GDPR compliance"
        )

    return {"status": "success"}
```

---

## 9. Scaling & Cost Optimization

### Render Plan Tiers

| Service | Starter ($7/mo) | Standard ($25/mo) | Pro ($85/mo) |
|---------|-----------------|-------------------|--------------|
| **Web** | 512MB RAM, 0.5 CPU | 2GB RAM, 1 CPU | 4GB RAM, 2 CPU |
| **Auto-scaling** | No | Yes (1-10 instances) | Yes (1-100 instances) |
| **Zero-downtime** | Yes | Yes | Yes |
| **Custom domains** | Yes | Yes | Yes |
| **PostgreSQL** | 1GB, 256MB RAM | 10GB, 1GB RAM | 256GB, 8GB RAM |
| **Connections** | 25 | 120 | 300 |

### Scaling Strategy

**Phase 1: Launch (1-100 shops)**
```yaml
Services:
- API: Starter ($7)
- Worker: Starter ($7)
- DB: Starter ($7)
- Redis: Free
Total: $21/mo
```

**Phase 2: Growth (100-1,000 shops)**
```yaml
Services:
- API: Standard with auto-scaling 1-3 instances ($25)
- Worker: Standard ($25)
- DB: Standard ($20)
- Redis: Starter ($10)
Total: $80/mo
```

**Phase 3: Scale (1,000-10,000 shops)**
```yaml
Services:
- API: Pro with auto-scaling 3-10 instances ($85 + overages)
- Worker: Pro with 2-5 instances ($85 x 3 = $255)
- DB: Pro ($200)
- Redis: Standard ($30)
Total: $570/mo
```

### Auto-Scaling Configuration

**In render.yaml:**
```yaml
services:
  - type: web
    name: ecomdash-api
    plan: standard  # Required for auto-scaling
    scaling:
      minInstances: 1
      maxInstances: 10
      targetMemoryPercent: 75  # Scale when memory > 75%
      targetCPUPercent: 75     # Scale when CPU > 75%
      targetRequestsPerSecond: 100  # Scale when RPS > 100
```

**How it works:**
- Render monitors CPU, memory, and request rate
- Automatically spins up new instances when thresholds exceeded
- Routes traffic via load balancer
- Spins down instances when load decreases

### Database Optimization

**1. Connection Pooling:**

Already configured in your `database.py`:
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,              # Keep 20 connections ready
    max_overflow=10,           # Allow 10 extra under load
    pool_pre_ping=True,        # Verify connection before use
    pool_recycle=3600,         # Recycle connections hourly
)
```

**2. Indexing:**

```sql
-- Ensure indexes on frequently queried columns
CREATE INDEX CONCURRENTLY idx_products_shop_id ON products(shop_id);
CREATE INDEX CONCURRENTLY idx_orders_shop_processed ON orders(shop_id, processed_at DESC);
CREATE INDEX CONCURRENTLY idx_insights_shop_created ON insights(shop_id, created_at DESC);

-- Composite indexes for complex queries
CREATE INDEX CONCURRENTLY idx_analytics_events_shop_time
ON analytics_event(shop_id, timestamp DESC);
```

**3. Query Optimization:**

```python
# Bad: N+1 query problem
shops = await db.scalars(select(Shop))
for shop in shops:
    products = await db.scalars(select(Product).where(Product.shop_id == shop.id))

# Good: Use joinedload
from sqlalchemy.orm import joinedload

shops = await db.scalars(
    select(Shop).options(joinedload(Shop.products))
)
```

**4. Read Replicas (Standard+ plan):**

```python
# Primary for writes
primary_engine = create_async_engine(settings.DATABASE_URL)

# Replica for reads
replica_engine = create_async_engine(settings.DATABASE_REPLICA_URL)

# Route queries
async def get_readonly_db():
    async with AsyncSession(replica_engine) as session:
        yield session

@router.get("/api/products")
async def list_products(db: AsyncSession = Depends(get_readonly_db)):
    # Reads go to replica
    ...
```

### Caching Strategy

**1. Redis Caching:**

```python
import redis.asyncio as redis
from functools import wraps

redis_client = redis.from_url(settings.REDIS_URL)

async def get_cached(key: str):
    """Get cached value."""
    value = await redis_client.get(key)
    return json.loads(value) if value else None

async def set_cached(key: str, value: Any, ttl: int = 3600):
    """Set cached value with TTL."""
    await redis_client.setex(key, ttl, json.dumps(value))

# Decorator for endpoint caching
def cache_response(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function + args
            cache_key = f"{func.__name__}:{hash(str(args))}"

            # Try cache first
            cached = await get_cached(cache_key)
            if cached:
                return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await set_cached(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

# Usage
@router.get("/api/dashboard/stats")
@cache_response(ttl=300)  # Cache for 5 minutes
async def get_dashboard_stats(shop_id: UUID):
    # Expensive computation
    ...
```

**2. Cache Invalidation:**

```python
@router.post("/api/products")
async def create_product(product_data: ProductCreate, shop_id: UUID):
    # Create product
    product = await product_service.create(db, product_data)

    # Invalidate cache
    await redis_client.delete(f"get_dashboard_stats:{shop_id}")

    return product
```

### Background Jobs Optimization

**ARQ Worker Configuration:**

`backend/app/services/job_queue.py`:
```python
class WorkerSettings:
    functions = [sync_shopify_data, generate_insights, send_notification]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    # Worker tuning
    max_jobs = 10              # Process 10 jobs concurrently
    job_timeout = 300          # 5 minutes max per job
    keep_result = 3600         # Keep results for 1 hour
    max_tries = 3              # Retry failed jobs 3 times
    retry_delay = 60           # Wait 60s before retry
```

**Scaling Workers:**
```yaml
# render.yaml - Multiple worker instances
services:
  - type: worker
    name: ecomdash-worker-1
    numInstances: 1
    # ... config

  - type: worker
    name: ecomdash-worker-2
    numInstances: 1
    # ... config
```

### CDN for Static Assets

**Render Static Sites include CDN:**
- Automatic CDN distribution
- Edge caching (reduce latency)
- No extra configuration needed

**For API responses (optional):**
- Use Cloudflare in front of Render
- Cache GET requests at edge
- Set appropriate `Cache-Control` headers

```python
from fastapi import Response

@router.get("/api/public/stats")
async def public_stats():
    data = await compute_stats()
    return Response(
        content=json.dumps(data),
        media_type="application/json",
        headers={
            "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
        }
    )
```

### Cost Optimization Tips

1. **Start Small:**
   - Use Starter plans initially
   - Upgrade only when hitting resource limits

2. **Monitor Usage:**
   ```bash
   # Check instance metrics
   render logs ecomdash-api --tail | grep "memory"

   # Database usage
   render psql ecomdash-db -c "SELECT pg_database_size('ecomdash');"
   ```

3. **Optimize Docker Images:**
   ```dockerfile
   # Use multi-stage builds (already in your Dockerfile)
   FROM python:3.11-slim AS builder
   # Install deps

   FROM python:3.11-slim
   # Copy only runtime files
   COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
   ```

4. **Reduce Build Times:**
   ```dockerfile
   # Cache dependencies layer
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Then copy code (changes frequently)
   COPY . .
   ```

5. **Use Free Tier Services:**
   - Redis Free: Sufficient for job queue (25MB)
   - Frontend Static: Free hosting
   - Render provides free SSL

6. **Database Disk Optimization:**
   ```sql
   -- Regularly vacuum
   VACUUM ANALYZE;

   -- Drop unused indexes
   SELECT schemaname, tablename, indexname FROM pg_indexes WHERE schemaname = 'public';
   ```

---

## 10. Monitoring & Observability

### Health Checks

**Already Implemented:**

`backend/app/routers/health.py`:
```python
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }

@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe (checks dependencies)."""
    try:
        # Check database
        await db.execute(text("SELECT 1"))

        # Check Redis
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()

        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

**Render Configuration:**

```yaml
# render.yaml
services:
  - type: web
    name: ecomdash-api
    healthCheckPath: /health  # Render monitors this endpoint
```

### Structured Logging

**Already Implemented:**

`backend/app/core/logging.py`:
```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.ENVIRONMENT == "production" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

**Usage:**
```python
# Structured logging
logger.info(
    "order_processed",
    shop_id=str(shop.id),
    order_id=str(order.id),
    total_price=order.total_price,
    duration_ms=elapsed_time,
)

# Production output (JSON)
{
  "event": "order_processed",
  "shop_id": "uuid...",
  "order_id": "uuid...",
  "total_price": 150.00,
  "duration_ms": 234,
  "timestamp": "2026-01-09T12:34:56.789Z",
  "level": "info"
}
```

**Viewing Logs:**
```bash
# Live tail
render logs ecomdash-api --tail

# Filter by level
render logs ecomdash-api --tail | grep '"level":"error"'

# Download logs
render logs ecomdash-api --since 1h > logs.txt
```

### Sentry Error Tracking

**Already Configured:**

`pyproject.toml` includes `sentry-sdk[fastapi]>=1.39.1`

**Setup:**

```python
# backend/app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% performance monitoring
        profiles_sample_rate=0.1,  # 10% profiling
    )
```

**Environment Variable:**
```bash
# Get from sentry.io
SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project>
```

**Features:**
- Automatic exception capture
- Request breadcrumbs
- Performance monitoring (APM)
- User context tracking
- Release tracking

**Custom Context:**
```python
from sentry_sdk import set_context, set_user

# Add shop context to errors
set_context("shop", {
    "id": str(shop.id),
    "domain": shop.domain,
})

# Track user (if applicable)
set_user({"id": str(user_id), "email": user_email})
```

### Prometheus Metrics

**Already Configured:**

`pyproject.toml` includes `prometheus-client>=0.19.0`

**Implementation:**

```python
# backend/app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

shopify_api_calls_total = Counter(
    'shopify_api_calls_total',
    'Total Shopify API calls',
    ['shop_domain', 'endpoint', 'status']
)

active_shops = Gauge(
    'active_shops',
    'Number of active shops'
)

# Middleware to track metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Scraping with Prometheus:**

Deploy Prometheus separately and configure scraping:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ecomdash-api'
    static_configs:
      - targets: ['ecomdash-api.onrender.com']
    metrics_path: '/metrics'
```

### Uptime Monitoring

**Recommended Services:**
1. **UptimeRobot** (free tier available)
2. **Pingdom**
3. **Better Uptime**
4. **StatusCake**

**Configuration:**
- Monitor: `https://ecomdash-api.onrender.com/health`
- Interval: 1 minute
- Alerts: Email, Slack, SMS

### Dashboard (Grafana)

**Setup:**
1. Deploy Grafana on Render (free tier)
2. Connect to Prometheus data source
3. Import pre-built FastAPI dashboard

**Key Metrics to Track:**
- Request rate (RPS)
- Error rate (4xx, 5xx)
- Response time (p50, p95, p99)
- Database query duration
- Shopify API call latency
- Active shops count
- Background job queue length

### Log Aggregation (Optional)

**For Production at Scale:**

Use log aggregation service:
1. **Logz.io** (ELK stack as a service)
2. **Datadog**
3. **New Relic**

**Integration:**
```python
# Send logs to external service
import logging
import logzio

# Configure handler
logzio_handler = logzio.LogzioHandler(token=settings.LOGZIO_TOKEN)
logging.root.addHandler(logzio_handler)
```

---

## 11. CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Render

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-for-ci
          ENCRYPTION_KEY: test-encryption-key-for-ci
        run: |
          cd backend
          pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install ruff mypy

      - name: Run ruff
        run: |
          cd backend
          ruff check .

      - name: Run mypy
        run: |
          cd backend
          mypy app

  deploy:
    runs-on: ubuntu-latest
    needs: [test, lint]
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Trigger Render Deploy
        run: |
          # Render auto-deploys on push to main
          echo "Deployment triggered automatically by Render"

      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployment to Render completed'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        if: always()
```

### Pre-Deployment Checks

**Pre-commit Hooks:**

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.11
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

**Install:**
```bash
pip install pre-commit
pre-commit install
```

### Database Migration in CI/CD

**Pre-Deploy Command in render.yaml:**

```yaml
services:
  - type: web
    name: ecomdash-api
    runtime: docker
    dockerfilePath: ./backend/Dockerfile
    dockerContext: ./backend
    preDeployCommand: "alembic upgrade head"  # Run before new version starts
```

**How it works:**
1. Render builds new Docker image
2. Runs `preDeployCommand` with new code
3. If migrations succeed, deploys new version
4. If migrations fail, keeps old version running

### Staging Environment

**Create separate Blueprint for staging:**

`render-staging.yaml`:
```yaml
services:
  - type: web
    name: ecomdash-api-staging
    runtime: docker
    dockerfilePath: ./backend/Dockerfile
    dockerContext: ./backend
    branch: staging  # Deploy from staging branch
    region: oregon
    plan: starter
    envVars:
      - key: ENVIRONMENT
        value: staging
      - key: DATABASE_URL
        fromDatabase:
          name: ecomdash-db-staging
          property: connectionString
      # ... other vars

databases:
  - name: ecomdash-db-staging
    databaseName: ecomdash_staging
    user: ecomdash_staging
    region: oregon
    plan: starter
```

**Deployment Flow:**
```
Feature Branch → PR → Merge to staging → Auto-deploy to staging
                       ↓ Test on staging
                       ↓ Approve
Merge staging → main → Auto-deploy to production
```

### Rollback Strategy

**Render provides rollback via Dashboard:**
1. Go to service page
2. Navigate to **Deploys** tab
3. Click **Rollback** on previous successful deploy

**CLI Rollback:**
```bash
# List recent deploys
render deploys list ecomdash-api

# Rollback to specific deploy
render deploy rollback <deploy-id>
```

**Database Rollback:**
```bash
# SSH into service
render shell ecomdash-api

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>
```

**Backup Before Deploy (Recommended):**
```bash
# Create backup before deployment
render backup create ecomdash-db
```

---

## 12. Step-by-Step Deployment Procedure

### Prerequisites Checklist

- [ ] GitHub/GitLab repository created
- [ ] Render account created (sign up at render.com)
- [ ] Shopify Partners account (if using Shopify app)
- [ ] OpenAI API key (for AI features)
- [ ] Resend API key (optional, for emails)
- [ ] Sentry account (optional, for error tracking)

### Step 1: Prepare Repository

**1.1 Clone and Configure:**

```bash
# Clone repository
git clone https://github.com/yourusername/EcomDashQ1BetaCohort.git
cd EcomDashQ1BetaCohort

# Verify render.yaml exists
cat render.yaml

# Create .gitignore (if not exists)
cat > .gitignore <<EOF
.env
.env.*
!.env.example
__pycache__/
*.pyc
.pytest_cache/
.coverage
*.db
node_modules/
EOF

# Commit and push
git add .
git commit -m "chore: prepare for Render deployment"
git push origin main
```

**1.2 Verify Dockerfiles:**

Ensure these files exist:
- `backend/Dockerfile` (API)
- `backend/Dockerfile.worker` (Worker)

Test locally:
```bash
# Build API image
cd backend
docker build -t ecomdash-api -f Dockerfile .

# Build worker image
docker build -t ecomdash-worker -f Dockerfile.worker .

# Test run
docker run -p 8000:8000 ecomdash-api
```

### Step 2: Create Render Account & Connect Git

**2.1 Sign Up:**
- Visit [render.com](https://render.com)
- Click **Get Started**
- Choose **Sign up with GitHub** (recommended)

**2.2 Connect Repository:**
- Authorize Render to access your repositories
- Select **All repositories** or specific repo

### Step 3: Deploy via Blueprint

**3.1 Create Blueprint:**
- In Render Dashboard, click **New +**
- Select **Blueprint**
- Choose your repository
- Select branch: **main**
- Render detects `render.yaml`

**3.2 Review Configuration:**

Render shows preview of services to be created:
```
✓ ecomdash-api (Web Service)
✓ ecomdash-worker (Worker)
✓ ecomdash-frontend (Static Site)
✓ ecomdash-db (PostgreSQL)
✓ ecomdash-redis (Redis)
✓ ecomdash-secrets (Environment Group)
```

**3.3 Click "Apply":**
- Render provisions all resources
- This takes 5-10 minutes

### Step 4: Configure Environment Variables

**4.1 Navigate to Environment Group:**
- Dashboard → **Environment** → **Environment Groups**
- Find **ecomdash-secrets**

**4.2 Add Required Secrets:**

```bash
# Shopify credentials (from Partners Dashboard)
SHOPIFY_API_KEY=<your_api_key>
SHOPIFY_API_SECRET=<your_api_secret>

# OpenAI (from platform.openai.com)
OPENAI_API_KEY=sk-<your_key>

# Optional: Resend for emails
RESEND_API_KEY=re_<your_key>

# Optional: Sentry for error tracking
SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project>
```

**4.3 Update SHOPIFY_APP_URL:**
- Go to **ecomdash-api** service
- Navigate to **Environment** tab
- Find `SHOPIFY_APP_URL`
- Set to: `https://ecomdash-api.onrender.com` (your actual URL)

### Step 5: Initialize Database

**5.1 Wait for Database to be Ready:**
```bash
# Check database status
render databases list

# Should show "available"
```

**5.2 Enable Extensions:**
```bash
# Open psql shell
render psql ecomdash-db

# Run in psql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\dx  # Verify extensions

# Exit
\q
```

**5.3 Run Migrations:**

**Option A: Via preDeployCommand (Recommended):**

Your `render.yaml` should already include:
```yaml
preDeployCommand: "alembic upgrade head"
```

If not, add it and push:
```bash
# Edit render.yaml
# Add preDeployCommand line
git add render.yaml
git commit -m "feat: add automatic migrations"
git push
```

**Option B: Manual SSH:**
```bash
# SSH into API service
render shell ecomdash-api

# Run migrations
cd /app
alembic upgrade head

# Verify
alembic current
```

### Step 6: Verify Deployment

**6.1 Check Health:**
```bash
# API health check
curl https://ecomdash-api.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production"
}
```

**6.2 Check Readiness:**
```bash
curl https://ecomdash-api.onrender.com/health/ready

# Expected response:
{"status": "ready"}
```

**6.3 View Logs:**
```bash
# API logs
render logs ecomdash-api --tail

# Worker logs
render logs ecomdash-worker --tail

# Database logs
render logs ecomdash-db --tail
```

**6.4 Test Database Connection:**
```bash
render psql ecomdash-db -c "SELECT count(*) FROM shops;"

# Expected: 0 (no shops yet)
```

### Step 7: Configure Shopify App (If Applicable)

**7.1 Update App Settings in Partners Dashboard:**

- Go to [partners.shopify.com](https://partners.shopify.com)
- Select your app
- Update **App URL:** `https://ecomdash-api.onrender.com`
- Update **Allowed redirection URL(s):**
  ```
  https://ecomdash-api.onrender.com/auth/callback
  https://ecomdash-frontend.onrender.com/auth/callback
  ```

**7.2 Configure Webhooks:**

In Partners Dashboard → **Webhooks**:
- **app/uninstalled:** `https://ecomdash-api.onrender.com/webhooks/app_uninstalled`
- **shop/redact:** `https://ecomdash-api.onrender.com/webhooks/shop_redact`
- **customers/data_request:** `https://ecomdash-api.onrender.com/webhooks/customer_data_request`
- **customers/redact:** `https://ecomdash-api.onrender.com/webhooks/customer_redact`

### Step 8: Test End-to-End

**8.1 Install App on Test Store:**
- Create development store in Partners Dashboard
- Install your app on test store
- Complete OAuth flow

**8.2 Verify Shop Creation:**
```bash
render psql ecomdash-db -c "SELECT id, domain, created_at FROM shops;"

# Should show your test store
```

**8.3 Test API Endpoints:**
```bash
# Get shop info
curl "https://ecomdash-api.onrender.com/api/shops/<shop_domain>"

# Get insights
curl "https://ecomdash-api.onrender.com/api/insights?shop=<shop_domain>"
```

**8.4 Test Frontend:**
```bash
# Visit frontend
open https://ecomdash-frontend.onrender.com
```

### Step 9: Monitor First 24 Hours

**9.1 Set Up Alerts:**
- Configure UptimeRobot or similar
- Monitor `/health` endpoint every 5 minutes

**9.2 Watch Logs:**
```bash
# Keep logs tailing in terminal
render logs ecomdash-api --tail &
render logs ecomdash-worker --tail &
```

**9.3 Check Sentry:**
- Visit sentry.io dashboard
- Verify errors are being captured

**9.4 Monitor Metrics:**
```bash
# Check instance stats in Dashboard
# Look for:
# - CPU usage < 75%
# - Memory usage < 75%
# - No 5xx errors
```

### Step 10: Post-Deployment Tasks

**10.1 Enable Auto-Deploy:**
- Already enabled via `autoDeploy: true` in `render.yaml`
- Verify in Dashboard: Service → **Settings** → **Auto-Deploy**

**10.2 Configure Custom Domain (Optional):**
- Dashboard → Service → **Settings** → **Custom Domain**
- Add domain: `api.yourdomain.com`
- Update DNS:
  ```
  CNAME api.yourdomain.com → ecomdash-api.onrender.com
  ```

**10.3 Set Up Backups:**
```bash
# Create initial backup
render backup create ecomdash-db

# Verify backups
render backups list ecomdash-db
```

**10.4 Document Deployment:**
- Record all service URLs
- Document environment variables
- Create runbook for common operations

---

## 13. Troubleshooting

### Common Issues

**Issue 1: Build Fails**

**Symptom:**
```
Error: failed to solve: failed to compute cache key
```

**Solution:**
```bash
# Check Dockerfile syntax
cd backend
docker build -t test .

# Common fixes:
# 1. Verify COPY paths are correct
# 2. Check requirements.txt exists
# 3. Ensure .dockerignore doesn't exclude needed files
```

**Issue 2: Database Connection Fails**

**Symptom:**
```
asyncpg.exceptions.InvalidPasswordError: password authentication failed
```

**Solution:**
```bash
# Verify DATABASE_URL is set correctly
render env list ecomdash-api | grep DATABASE_URL

# Should be: postgresql://ecomdash:<password>@...

# If missing, re-link database
# Dashboard → Service → Environment → DATABASE_URL → Link Database
```

**Issue 3: Migrations Fail**

**Symptom:**
```
alembic.util.exc.CommandError: Can't locate revision identified by '<hash>'
```

**Solution:**
```bash
# SSH into service
render shell ecomdash-api

# Check current version
alembic current

# Check migration history
alembic history

# If out of sync, stamp current version
alembic stamp head

# Or start fresh (DANGER: drops all data)
alembic downgrade base
alembic upgrade head
```

**Issue 4: 503 Service Unavailable**

**Symptom:**
```
curl https://ecomdash-api.onrender.com/health
-> 503 Service Unavailable
```

**Solution:**
```bash
# Check logs
render logs ecomdash-api --tail

# Common causes:
# 1. App not listening on PORT
#    → Verify Dockerfile: CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# 2. Health check failing
#    → Test locally: curl localhost:8000/health
# 3. Startup taking too long
#    → Increase startup timeout in Dashboard
```

**Issue 5: Worker Not Processing Jobs**

**Symptom:**
```
Jobs queued in Redis but not processed
```

**Solution:**
```bash
# Check worker logs
render logs ecomdash-worker --tail

# Verify Redis connection
render shell ecomdash-worker
python -c "import redis; r = redis.from_url('$REDIS_URL'); print(r.ping())"

# Check ARQ worker is running
ps aux | grep arq

# Restart worker
# Dashboard → ecomdash-worker → Manual Deploy
```

**Issue 6: Shopify OAuth Fails**

**Symptom:**
```
Error: invalid_request - The redirect_uri is not whitelisted
```

**Solution:**
```bash
# Verify redirect URI in Shopify Partners Dashboard
# Must exactly match: https://ecomdash-api.onrender.com/auth/callback

# Check SHOPIFY_APP_URL environment variable
render env list ecomdash-api | grep SHOPIFY_APP_URL

# Should match your actual Render URL
```

**Issue 7: CORS Errors**

**Symptom:**
```
Access to fetch at 'https://ecomdash-api.onrender.com' has been blocked by CORS policy
```

**Solution:**
```bash
# Check ALLOWED_ORIGINS
render env list ecomdash-api | grep ALLOWED_ORIGINS

# Should include your frontend URL:
ALLOWED_ORIGINS=https://admin.shopify.com,https://ecomdash-frontend.onrender.com

# Update if needed
render env set ecomdash-api ALLOWED_ORIGINS="https://admin.shopify.com,https://ecomdash-frontend.onrender.com"
```

### Debug Commands

```bash
# View environment variables
render env list ecomdash-api

# View service info
render services get ecomdash-api

# View recent deploys
render deploys list ecomdash-api

# Open psql shell
render psql ecomdash-db

# SSH into service
render shell ecomdash-api

# Download logs
render logs ecomdash-api --since 1h > logs.txt

# Check Redis
render shell ecomdash-api
python -c "import redis; r = redis.from_url('$REDIS_URL'); print(r.info())"
```

---

## 14. Production Checklist

### Before Launch

#### Security
- [ ] All secrets set in Render environment variables
- [ ] `sync: false` for all secrets in `render.yaml`
- [ ] HTTPS enforced (automatic on Render)
- [ ] CORS configured with explicit origins (no `*`)
- [ ] Rate limiting enabled
- [ ] HMAC verification for webhooks
- [ ] Token encryption verified (Fernet)
- [ ] SQL injection protection (using ORM)
- [ ] Input validation (Pydantic schemas)

#### Database
- [ ] PostgreSQL plan sufficient (Starter = $7, 1GB)
- [ ] pgvector extension enabled
- [ ] uuid-ossp extension enabled
- [ ] All migrations run successfully
- [ ] Indexes created on frequently queried columns
- [ ] Connection pooling configured (pool_size=20)
- [ ] Backup schedule verified (daily for Starter)

#### Performance
- [ ] Redis connection configured
- [ ] Caching strategy implemented
- [ ] Database queries optimized (no N+1)
- [ ] Background jobs configured (ARQ)
- [ ] Docker images optimized (multi-stage build)
- [ ] Auto-scaling configured (if using Standard+ plan)

#### Monitoring
- [ ] Sentry configured for error tracking
- [ ] Structured logging enabled (JSON in production)
- [ ] Health check endpoint working (`/health`)
- [ ] Readiness probe working (`/health/ready`)
- [ ] Prometheus metrics exposed (`/metrics`)
- [ ] Uptime monitoring configured (UptimeRobot)

#### Deployment
- [ ] `render.yaml` Blueprint validated
- [ ] All services deployed successfully
- [ ] Environment variables set correctly
- [ ] `preDeployCommand` configured for migrations
- [ ] Auto-deploy enabled on main branch
- [ ] Staging environment configured (optional)
- [ ] Rollback procedure documented

#### Shopify Integration
- [ ] App created in Partners Dashboard (if applicable)
- [ ] OAuth redirect URLs whitelisted
- [ ] SHOPIFY_API_KEY and SHOPIFY_API_SECRET set
- [ ] Webhooks registered (app/uninstalled, GDPR)
- [ ] HMAC verification working
- [ ] Test installation completed successfully

#### Testing
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] End-to-end test completed on staging
- [ ] Load testing performed (optional)
- [ ] Security scan completed (optional)

### Post-Launch

#### Week 1
- [ ] Monitor error rate in Sentry
- [ ] Check CPU/memory usage
- [ ] Verify database performance
- [ ] Review logs for anomalies
- [ ] Test webhook delivery
- [ ] Verify backup creation

#### Month 1
- [ ] Review cost vs. plan limits
- [ ] Analyze slow queries
- [ ] Check cache hit rate
- [ ] Review security logs
- [ ] Update dependencies (security patches)
- [ ] Rotate secrets (if scheduled)

#### Quarterly
- [ ] Database vacuum and analyze
- [ ] Review and optimize indexes
- [ ] Audit access controls
- [ ] Update documentation
- [ ] Review scaling strategy
- [ ] Plan for growth

---

## 15. Quick Reference

### Essential Commands

```bash
# Authentication
render login

# List services
render services list

# View logs
render logs <service-name> --tail

# SSH into service
render shell <service-name>

# Database shell
render psql <database-name>

# Environment variables
render env list <service-name>
render env set <service-name> KEY=value

# Deployments
render deploy <service-name>
render deploy <service-name> --commit <hash>
render deploys list <service-name>

# Backups
render backup create <database-id>
render backups list <database-id>
```

### Important URLs

- **Render Dashboard:** https://dashboard.render.com
- **Render Docs:** https://render.com/docs
- **Shopify Partners:** https://partners.shopify.com
- **Sentry:** https://sentry.io
- **OpenAI Platform:** https://platform.openai.com

### Service URLs (After Deployment)

- **API:** `https://ecomdash-api.onrender.com`
- **Frontend:** `https://ecomdash-frontend.onrender.com`
- **Health Check:** `https://ecomdash-api.onrender.com/health`
- **API Docs:** `https://ecomdash-api.onrender.com/docs`

### Support

**Render Support:**
- Email: support@render.com
- Community: https://community.render.com
- Status: https://status.render.com

**EcomDash Issues:**
- GitHub Issues: (your repo)/issues
- Documentation: (your repo)/README.md

---

## Conclusion

This guide provides a comprehensive, production-ready deployment strategy for EcomDash V2 on Render.com. Follow the step-by-step procedures, implement the security best practices, and monitor your deployment using the observability tools outlined.

**Key Takeaways:**

1. **Use Render Blueprints** (`render.yaml`) for reproducible infrastructure
2. **Implement multi-tenant isolation** at the database level with `shop_id`
3. **Encrypt all OAuth tokens** using Fernet symmetric encryption
4. **Configure auto-scaling** for growth (Standard plan and above)
5. **Monitor proactively** with Sentry, Prometheus, and uptime checks
6. **Test thoroughly** in staging before promoting to production
7. **Document everything** for your team

**Next Steps:**

1. Complete the deployment following [Step-by-Step Deployment Procedure](#12-step-by-step-deployment-procedure)
2. Test with a development store
3. Set up monitoring and alerts
4. Deploy to staging for QA
5. Launch to production
6. Monitor for 24-48 hours
7. Iterate and optimize

Good luck with your deployment!

---

**Document Version:** 2.0.0
**Last Updated:** 2026-01-09
**Maintained By:** EcomDash Team
