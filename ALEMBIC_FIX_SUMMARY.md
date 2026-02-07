# Alembic Migration Fix Summary

**Date:** 2026-02-04
**Status:** ✅ **RESOLVED**

---

## Issues Fixed

### 1. **DATABASE_URL Configuration** ✅

**Problem:**
- Settings was loading from `.env` which pointed to localhost docker postgres
- User prefers using `.env.local` for local overrides

**Solution:**
- Fixed `.env.local` format (added `DATABASE_URL=` prefix)
- Updated `app/core/config.py` to load from both `.env` and `.env.local`
- `.env.local` now takes precedence (as expected)

**Files Changed:**
- `backend/.env.local` - Added `DATABASE_URL=` prefix
- `backend/app/core/config.py` - Changed `env_file=".env"` to `env_file=(".env", ".env.local")`

### 2. **Migration Chain Broken** ✅

**Problem:**
- Migration 001 has revision ID: `'001_initial'`
- Migration 002 was looking for: `'001'` (mismatched)
- Alembic couldn't find the parent revision

**Solution:**
- Fixed `002_analytics_schema.py` down_revision to match: `'001_initial'`

**File Changed:**
- `backend/alembic/versions/002_analytics_schema.py` (line 16)

---

## Verification Results

### ✅ Connection Test
```
✅ Connected to PostgreSQL
Version: PostgreSQL 18.1 (Debian 18.1-1.pgdg12+2)
Host: dpg-d5jn6l6mcj7s738fnrig-a.oregon-postgres.render.com
```

### ✅ Migrations Applied
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial
INFO  [alembic.runtime.migration] Running upgrade 001_initial -> 002
```

### ✅ Tables Created (16 total)
```
- Session
- alembic_version
- analysis_results
- analytics_events
- analytics_sessions
- code_submissions
- conversion_events
- conversion_funnels
- heatmap_data
- insights
- notification_preferences
- orders
- products
- session_replays
- shops
- traffic_metrics
```

---

## Configuration Summary

### Working Setup

**File:** `backend/.env.local`
```bash
RENDER_API_KEY=rnd_***
DATABASE_URL=postgresql://ecomdash:***@dpg-d5jn6l6mcj7s738fnrig-a.oregon-postgres.render.com/ecomdash
```

**Config Priority:**
1. `.env.local` (highest priority) ← **USER OVERRIDES HERE**
2. `.env` (defaults for local development)
3. Environment variables (production)

### SSL Configuration

**No explicit SSL config needed!**
- asyncpg 0.31.0 automatically enables SSL for Render domains
- Connection string uses standard format (no `?sslmode=require` needed)
- Code in `database.py` auto-converts `postgresql://` → `postgresql+asyncpg://`

---

## Next Steps

### ✅ Backend Ready
Your backend can now:
- Connect to Render PostgreSQL
- Run migrations successfully
- Store real data (not demo data)

### 🎯 Connect Frontend to Backend

Update `growzilla-beta/.env` (or wherever frontend env is):
```bash
SHOPIFY_API_URL=https://ecomdash-api.onrender.com
```

Then follow EXECUTION_PLAN_SHOPIFY_EMBEDDED_APP.md:
- Phase 1: Add App Bridge integration
- Phase 2: OAuth flow
- Phase 3: Data sync with cursors

### Test Backend API

```bash
# Health check
curl https://ecomdash-api.onrender.com/health

# Dashboard stats (should return real data once shop is synced)
curl https://ecomdash-api.onrender.com/api/dashboard/stats?shop_id=YOUR_SHOP_ID
```

---

## Technical Details

### Database Connection Flow

1. **Settings Load** (`app/core/config.py`):
   ```python
   model_config = SettingsConfigDict(
       env_file=(".env", ".env.local"),  # ← .env.local overrides .env
       env_file_encoding="utf-8",
       case_sensitive=False,
       extra="ignore",
   )
   ```

2. **Alembic Uses Settings** (`alembic/env.py`):
   ```python
   from app.core.config import settings

   def get_url() -> str:
       url = str(settings.database_url)
       if url.startswith("postgresql://"):
           url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
       return url
   ```

3. **Engine Creation** (`app/core/database.py`):
   - Uses same URL transformation
   - Adds connection pooling
   - SSL handled automatically by asyncpg

### Migration Chain

```
None → 001_initial → 002
       (shops,      (analytics_events,
        products,    analytics_sessions,
        orders,      conversion_events,
        insights)    conversion_funnels,
                     heatmap_data,
                     traffic_metrics,
                     session_replays,
                     notification_preferences)
```

---

## Lessons Learned

### 1. **Pydantic Settings Priority**
- In Pydantic Settings v2.x, you must explicitly list multiple env files
- Format: `env_file=(".env", ".env.local")`
- Later files in tuple override earlier ones

### 2. **Alembic Revision IDs Must Match**
- Parent migration: `revision = '001_initial'`
- Child migration: `down_revision = '001_initial'` ← Must match exactly
- Common mistake: Using short name `'001'` when actual ID is `'001_initial'`

### 3. **asyncpg SSL Auto-Detection**
- asyncpg 0.31.0+ automatically enables SSL for non-localhost hosts
- Render domains (`.render.com`) are detected as requiring SSL
- No need for `?sslmode=require` or explicit `connect_args={"ssl": ...}`

---

## Troubleshooting Commands

### Check DATABASE_URL Resolution
```bash
cd backend
.venv/bin/python -c "
import sys; sys.path.insert(0, '.'
from app.core.config import settings
import re
url = str(settings.database_url)
print('URL:', re.sub(r':([^:@]+)@', ':***@', url))
print('Host:', url.split('@')[1].split('/')[0] if '@' in url else 'NO HOST')
"
```

### Test Connection
```bash
.venv/bin/python -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.core.database import engine
from sqlalchemy import text
async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT version()'))
        print(result.fetchone()[0])
asyncio.run(test())
"
```

### Check Migration Status
```bash
.venv/bin/alembic current
.venv/bin/alembic history
```

### List Tables
```bash
.venv/bin/python -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.core.database import engine
from sqlalchemy import text
async def tables():
    async with engine.connect() as conn:
        result = await conn.execute(text(\"\"\"
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
        \"\"\"))
        for row in result: print(row[0])
asyncio.run(tables())
"
```

---

## Files Modified

1. `backend/.env.local` - Added DATABASE_URL with proper format
2. `backend/app/core/config.py` - Load from both .env files
3. `backend/alembic/versions/002_analytics_schema.py` - Fixed down_revision

**Total changes:** 3 files, ~5 lines of code

---

## Status: ✅ READY FOR DEVELOPMENT

Your backend is now:
- ✅ Connected to Render PostgreSQL
- ✅ All 16 tables created
- ✅ Migrations working
- ✅ Ready to store real data

Next: Connect growzilla-beta frontend → ecomdash-api backend
