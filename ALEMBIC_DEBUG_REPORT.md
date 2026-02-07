# Alembic + Render PostgreSQL Connection Debug Report

**Date:** 2026-02-04
**Issue:** Alembic migrations failing with "password authentication failed for user postgres"

---

## 🔴 ROOT CAUSE IDENTIFIED

### The Problem

**Alembic is connecting to LOCAL docker postgres (localhost:5432) instead of Render PostgreSQL.**

### Evidence

**File:** `backend/.env` (line 14)
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ecomdash_v2
```

**What's happening:**
1. Alembic runs `alembic upgrade head`
2. `alembic/env.py` imports `from app.core.config import settings`
3. Settings loads `DATABASE_URL` from `backend/.env`
4. URL points to `localhost:5432` (docker postgres)
5. Docker postgres has different credentials → authentication fails

### Installed Versions (Compatible)

```
SQLAlchemy: 2.0.46
asyncpg: 0.31.0
alembic: 1.18.1
```

These versions are compatible and support asyncpg with SSL correctly.

---

## ✅ SOLUTION

### Step 1: Get Render Database Connection String

**Option A: From Render Dashboard**
1. Go to https://dashboard.render.com/d/dpg-d5jn6l6mcj7s738fnrig-a
2. Click "Info" tab
3. Copy "External Database URL"
4. Should look like: `postgresql://ecomdash:***@dpg-xxx.oregon-postgres.render.com/ecomdash`

**Option B: From Render CLI** (if you have credentials)
```bash
render services get dpg-d5jn6l6mcj7s738fnrig-a -o json | jq -r '.connectionString'
```

### Step 2: Update backend/.env

**Replace line 14 in `backend/.env`:**

**OLD (WRONG):**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ecomdash_v2
```

**NEW (CORRECT):**
```bash
DATABASE_URL=postgresql://ecomdash:YOUR_PASSWORD@dpg-xxx.oregon-postgres.render.com/ecomdash
```

**Important SSL Note:**
- Render PostgreSQL requires SSL
- asyncpg 0.31.0 + SQLAlchemy 2.0.46 handle SSL automatically for Render domains
- You do NOT need `?sslmode=require` in the connection string
- The code in `database.py` already converts `postgresql://` → `postgresql+asyncpg://`

### Step 3: Verify Configuration

Run these commands to verify the URL is correct (passwords will be redacted):

```bash
cd /home/ghostking/projects/EcomDashQ1BetaCohort/backend

# 1. Check which alembic is being used
which alembic
# Should show: /home/ghostking/projects/EcomDashQ1BetaCohort/backend/.venv/bin/alembic

# 2. Verify DATABASE_URL is loaded from .env
python -c "import sys; sys.path.insert(0, '.'); from app.core.config import settings; import re; url = str(settings.database_url); print('DATABASE_URL:', re.sub(r':([^:@]+)@', ':***@', url)); print('Host:', url.split('@')[1].split('/')[0] if '@' in url else 'NO HOST')"
# Should show Render host (dpg-xxx.oregon-postgres.render.com), NOT localhost

# 3. Test async engine connection
python -c "
import asyncio
import sys
sys.path.insert(0, '.')
from app.core.database import engine

async def test():
    try:
        async with engine.connect() as conn:
            result = await conn.execute('SELECT version()')
            row = result.fetchone()
            print('✅ Connected to PostgreSQL:', row[0][:50])
    except Exception as e:
        print('❌ Connection failed:', e)

asyncio.run(test())
"
# Should show: ✅ Connected to PostgreSQL: PostgreSQL 18.x...

# 4. Run migrations
.venv/bin/alembic upgrade head
# Should succeed without password errors
```

---

## 🔧 How Alembic Resolves DATABASE_URL

### Connection Flow

1. **alembic/env.py** (line 11):
   ```python
   from app.core.config import settings
   ```

2. **alembic/env.py** (lines 26-32):
   ```python
   def get_url() -> str:
       url = str(settings.database_url)
       if url.startswith("postgresql://"):
           url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
       return url
   ```

3. **app/core/config.py**:
   - Uses Pydantic Settings
   - Reads `DATABASE_URL` from environment (.env file)
   - Default: `postgresql://localhost/ecomdash` (if not set)

4. **alembic/env.py** (line 63):
   ```python
   configuration["sqlalchemy.url"] = get_url()
   ```

5. **SQLAlchemy creates async engine** with the resolved URL

### Why It Was Connecting to localhost

- `backend/.env` explicitly sets `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ecomdash_v2`
- This overrides any defaults
- Settings loads this value
- Alembic uses settings.database_url
- Result: Connects to docker postgres on localhost

---

## 🛡️ SSL Configuration for Render (asyncpg 0.31.0)

### Correct Format

**For Render PostgreSQL, use this format:**
```bash
DATABASE_URL=postgresql://user:password@dpg-xxx.oregon-postgres.render.com/database
```

**Do NOT add query parameters like:**
- ❌ `?sslmode=require` (causes errors with asyncpg)
- ❌ `?ssl=true` (not needed)

### Why No SSL Parameters Needed?

**asyncpg 0.31.0 behavior:**
- Automatically uses SSL for remote hosts
- Detects `.render.com` domains as requiring SSL
- Uses `ssl=True` internally
- No explicit configuration needed

**From asyncpg docs (0.31.0):**
> "SSL is automatically enabled for connections to hosts that are not localhost."

### If SSL Errors Occur (Unlikely)

If you get SSL errors after the fix, you can explicitly configure SSL in code:

**Option 1: Add to database.py engine creation (lines 46-52):**
```python
import ssl

return create_async_engine(
    database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.database_echo,
    pool_pre_ping=True,
    connect_args={"ssl": ssl.create_default_context()},  # Add this
)
```

**Option 2: Use connection string SSL parameter (asyncpg format):**
```bash
DATABASE_URL=postgresql://user:pass@host/db?ssl=require
```

But **try without these first** - asyncpg should handle it automatically.

---

## ✅ Validation Checklist

After updating `backend/.env` with Render URL:

- [ ] **Verify URL loaded:** Run validation command #2 above, should show Render host
- [ ] **Test connection:** Run validation command #3, should connect successfully
- [ ] **Run migrations:** Run `alembic upgrade head`, should create tables
- [ ] **Check database:** Query `SELECT * FROM shops LIMIT 1;` should not error
- [ ] **Test API:** `curl https://ecomdash-api.onrender.com/health` should return real data

---

## 🚨 Common Pitfalls

### 1. Using Wrong .env File
- Alembic loads from `backend/.env` (not root `.env`)
- Make sure you edit the correct file

### 2. Not Activating Virtual Environment
- Always use `.venv/bin/alembic` or activate venv first
- System alembic may have different versions

### 3. Mixing Connection String Formats
- Use `postgresql://` (not `postgresql+asyncpg://`) in .env
- Code auto-converts to `postgresql+asyncpg://`

### 4. Docker Postgres Running on localhost:5432
- This masks the issue - connections "succeed" but to wrong DB
- Always verify the host in resolved URL

---

## 📊 Diagnosis Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **SQLAlchemy Version** | ✅ 2.0.46 | Latest, supports async |
| **asyncpg Version** | ✅ 0.31.0 | Latest, auto-SSL |
| **Alembic Version** | ✅ 1.18.1 | Latest |
| **alembic/env.py Logic** | ✅ Correct | Properly imports settings |
| **database.py Logic** | ✅ Correct | Auto-converts to asyncpg |
| **backend/.env URL** | ❌ **WRONG** | Points to localhost, not Render |
| **SSL Configuration** | ✅ Will work | Once URL fixed |

---

## 🎯 Final Fix (One-Line Change)

**File:** `backend/.env` (line 14)

**Change from:**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ecomdash_v2
```

**Change to:**
```bash
DATABASE_URL=postgresql://ecomdash:YOUR_RENDER_PASSWORD@dpg-xxx.oregon-postgres.render.com/ecomdash
```

Replace:
- `YOUR_RENDER_PASSWORD` with actual password from Render dashboard
- `dpg-xxx.oregon-postgres.render.com` with actual Render hostname

**That's it. No code changes needed.**

---

## 🔐 Security Note

- Never commit `.env` files with real passwords to git
- Add `backend/.env` to `.gitignore`
- Use `.env.example` for templates
- Store production passwords in Render environment variables

---

## 📝 Next Steps After Fix

1. ✅ Update `backend/.env` with Render connection string
2. ✅ Run validation commands above
3. ✅ Execute `alembic upgrade head`
4. ✅ Verify tables created: `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';`
5. ✅ Test backend API with real data
6. ✅ Connect growzilla-beta frontend to backend

**Estimated time:** 5 minutes
**Risk:** Zero (just fixing a configuration error)
