# Onboarding New Shopify Stores Guide

**Date:** 2026-02-04
**Purpose:** How to add support for multiple Shopify stores with wildcard domain matching

---

## Current Limitation

Right now, each new Shopify store domain must be added manually to the `ALLOWED_ORIGINS` environment variable on Render.

**Example:**
```
ALLOWED_ORIGINS=https://growzilla-beta.onrender.com,https://admin.shopify.com,https://store1.myshopify.com,https://store2.myshopify.com
```

This becomes unmanageable with many stores.

---

## Solution: Wildcard Domain Support

Add regex pattern matching to allow ANY `*.myshopify.com` domain automatically.

### **One-Time Code Change**

**File:** `backend/app/main.py` (around line 84)

**Current Code:**
```python
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
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

**Updated Code:**
```python
# CORS with wildcard support for all Shopify stores
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # Specific domains (frontend, localhost)
    allow_origin_regex=r"https://.*\.myshopify\.com",  # ← ADD THIS LINE (any Shopify store)
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

### **What This Does**

✅ **Allows:**
- Any store: `https://any-store-name.myshopify.com`
- Your frontend: `https://growzilla-beta.onrender.com`
- Shopify Admin: `https://admin.shopify.com`
- Local dev: `http://localhost:3000`

❌ **Blocks:**
- Random domains: `https://evil-site.com`
- Non-Shopify domains: `https://fakeshop.com`

### **Deployment Steps**

1. **Update Code:**
   ```bash
   cd /home/ghostking/projects/EcomDashQ1BetaCohort/backend

   # Edit app/main.py and add the allow_origin_regex line
   ```

2. **Commit and Push:**
   ```bash
   git add app/main.py
   git commit -m "feat: add wildcard CORS support for all Shopify stores

   - Add allow_origin_regex for *.myshopify.com domains
   - Allows automatic onboarding of new stores
   - No need to manually add each store domain

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

   git push origin main
   ```

3. **Wait for Render Deploy:**
   - Auto-deploys in ~2-3 minutes
   - Check: https://dashboard.render.com/web/srv-d5jq6fsoud1c73fho0dg

4. **Verify:**
   ```bash
   # Test with any Shopify domain
   curl -X OPTIONS https://ecomdash-api.onrender.com/health \
     -H "Origin: https://any-new-store.myshopify.com" \
     -H "Access-Control-Request-Method: GET" \
     -s -D - | grep "access-control-allow-origin"

   # Should return: access-control-allow-origin: https://any-new-store.myshopify.com
   ```

---

## After Wildcard Support is Added

### **Environment Variable (Simplified)**

You can simplify `ALLOWED_ORIGINS` to just:
```
https://growzilla-beta.onrender.com,https://admin.shopify.com,http://localhost:3000
```

All `*.myshopify.com` domains work automatically via the regex.

### **Adding a New Store**

**Without wildcard (current):**
1. Get store domain: `new-store.myshopify.com`
2. Update Render env var to add it
3. Wait for redeploy
4. Test

**With wildcard (after code change):**
1. Nothing needed! ✅
2. Store works automatically

---

## Testing Wildcard Support

### **Test Different Store Domains**

```bash
# Test store 1
curl -X OPTIONS https://ecomdash-api.onrender.com/health \
  -H "Origin: https://test-store-1.myshopify.com" \
  -H "Access-Control-Request-Method: GET" \
  -s -D - | grep "access-control-allow-origin"

# Test store 2
curl -X OPTIONS https://ecomdash-api.onrender.com/health \
  -H "Origin: https://another-store.myshopify.com" \
  -H "Access-Control-Request-Method: GET" \
  -s -D - | grep "access-control-allow-origin"

# Both should return HTTP 200 with correct origin header
```

### **Verify Blocking Non-Shopify Domains**

```bash
# Should be blocked
curl -X OPTIONS https://ecomdash-api.onrender.com/health \
  -H "Origin: https://evil-site.com" \
  -H "Access-Control-Request-Method: GET" \
  -s -D - | grep "Disallowed\|access-control-allow-origin"

# Should see: "Disallowed CORS origin" or no access-control-allow-origin header
```

---

## Security Considerations

### **Why This is Safe**

✅ **Regex is Specific:**
```python
r"https://.*\.myshopify\.com"
```
- Must start with `https://`
- Must end with `.myshopify.com`
- Only matches legitimate Shopify stores

✅ **Still Requires Authentication:**
- CORS allows the browser to make requests
- Backend still validates session tokens
- Unauthorized requests still fail

✅ **No Open CORS:**
- Not using `allow_origins=["*"]` (dangerous)
- Specific pattern matching only

### **What's NOT Allowed**

❌ `http://anything.myshopify.com` - Must be HTTPS
❌ `https://myshopify.com` - Must have subdomain
❌ `https://evil.com/myshopify.com` - Must END with .myshopify.com
❌ `https://fakeshop.com` - Not a Shopify domain

---

## Regex Pattern Explained

```python
r"https://.*\.myshopify\.com"
```

| Part | Meaning |
|------|---------|
| `r"..."` | Raw string (treats backslashes literally) |
| `https://` | Must start with HTTPS protocol |
| `.*` | Match any characters (the store name) |
| `\.` | Literal dot (escaped) |
| `myshopify` | Literal text |
| `\.com` | Literal .com |

**Matches:**
- `https://store-name.myshopify.com` ✅
- `https://test-123.myshopify.com` ✅
- `https://any-valid-name.myshopify.com` ✅

**Doesn't Match:**
- `http://store.myshopify.com` (not HTTPS)
- `https://myshopify.com` (no subdomain)
- `https://store.otherdomain.com` (wrong domain)

---

## Alternative: Manual Store Management

If you prefer to control exactly which stores can connect:

### **Pros of Manual List:**
- More control over which stores connect
- Can revoke access by removing from list
- Audit trail of approved stores

### **Cons of Manual List:**
- Must update env var for each new store
- Requires redeploy for each addition
- Doesn't scale well with many stores

### **Hybrid Approach:**

Use BOTH:
```python
allow_origins=settings.allowed_origins,  # Explicit whitelist
allow_origin_regex=r"https://.*\.myshopify\.com",  # Auto-allow all Shopify
```

Then you can:
- Add non-Shopify domains to `ALLOWED_ORIGINS` (like your frontend)
- Auto-allow all Shopify stores via regex
- Block everything else

---

## Rollback Plan

If wildcard causes issues:

1. **Revert the code change:**
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Or just remove the line:**
   ```python
   # Comment out or delete this line:
   # allow_origin_regex=r"https://.*\.myshopify\.com",
   ```

3. **Go back to manual list:**
   ```
   ALLOWED_ORIGINS=https://growzilla-beta.onrender.com,https://admin.shopify.com,https://store1.myshopify.com,https://store2.myshopify.com
   ```

---

## Implementation Checklist

- [ ] Read this guide
- [ ] Decide: wildcard or manual list?
- [ ] If wildcard: Update `backend/app/main.py`
- [ ] Commit and push changes
- [ ] Wait for Render deploy
- [ ] Test with multiple store domains
- [ ] Verify non-Shopify domains blocked
- [ ] Update documentation
- [ ] Notify team of new capability

---

## Questions?

**Q: Can I use this for multiple app installations?**
A: Yes! Each store that installs your app will work automatically.

**Q: What about custom domains (not .myshopify.com)?**
A: Add them manually to `ALLOWED_ORIGINS` or create a second regex pattern.

**Q: Does this affect security?**
A: No. CORS only controls browser requests. Backend still validates session tokens.

**Q: Can I test this locally?**
A: Yes, but you need to run the backend locally and test with different Origin headers.

---

## Next Steps After Implementation

1. **Monitor Logs:** Watch for CORS errors from legitimate stores
2. **Update Tests:** Add tests for wildcard pattern matching
3. **Document:** Update API docs with onboarding flow
4. **Communicate:** Let merchants know they can install without manual approval

---

**File Created:** 2026-02-04
**Author:** Claude Sonnet 4.5
**Status:** Ready for implementation when needed
