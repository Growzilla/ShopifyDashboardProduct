"""
Health check and monitoring endpoints.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session

router = APIRouter(tags=["health"])


@router.get("/")
async def root() -> dict:
    """API root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@router.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.app_version,
    }


@router.get("/health/ready")
async def readiness_check(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Readiness probe - checks if the service can handle requests.
    Verifies database connectivity.
    """
    # Check database
    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    is_ready = db_status == "connected"

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": {
            "database": db_status,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/live")
async def liveness_check() -> dict:
    """
    Liveness probe - checks if the service is alive.
    Simple check that doesn't verify dependencies.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics")
async def metrics() -> dict:
    """
    Prometheus-compatible metrics endpoint.
    In production, use prometheus_client for proper formatting.
    """
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment,
    }


@router.post("/admin/bootstrap-shop")
async def bootstrap_shop(
    shop_domain: str,
    admin_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Temporary admin endpoint: reads Shopify access token from the Prisma
    Session table (shared PostgreSQL) and registers + syncs the shop.
    Requires the SECRET_KEY as admin_key for authorization.
    """
    from app.core.config import settings as app_settings

    if admin_key != app_settings.secret_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid admin key")

    if session is None:
        return {"error": "Database unavailable"}

    # Read access token from Prisma Session table
    result = await session.execute(
        text(
            'SELECT "accessToken", shop, scope FROM "Session" '
            "WHERE shop = :domain AND \"isOnline\" = false "
            "ORDER BY expires DESC NULLS LAST LIMIT 1"
        ),
        {"domain": shop_domain},
    )
    row = result.first()

    if not row:
        return {"error": f"No offline session found for {shop_domain}", "hint": "Has the store owner completed the OAuth install?"}

    access_token = row[0]
    scopes = row[2] or "read_products,read_orders"

    # Register shop in backend
    from app.core.security import encrypt_token
    from app.repositories.shop import ShopRepository

    repo = ShopRepository(session)
    encrypted = encrypt_token(access_token)
    shop, created = await repo.create_or_update(
        domain=shop_domain,
        access_token_encrypted=encrypted,
        scopes=scopes,
    )
    await session.commit()

    # Test Shopify API directly to get error details
    sync_result = {"status": "not_attempted"}
    try:
        # Verify token decryption
        from app.core.security import decrypt_token
        decrypted = decrypt_token(shop.access_token_encrypted)
        sync_result["token_decrypted_preview"] = decrypted[:12] + "..."
        sync_result["token_length"] = len(decrypted)

        # Test raw API call to verify token
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            test_resp = await http_client.post(
                f"https://{shop_domain}/admin/api/2025-01/graphql.json",
                json={"query": "{ shop { name myshopifyDomain } }"},
                headers={
                    "Content-Type": "application/json",
                    "X-Shopify-Access-Token": decrypted,
                },
            )
            sync_result["shopify_raw_status"] = test_resp.status_code
            sync_result["shopify_raw_body"] = test_resp.text[:300]

        # Also try with the raw token from session (not encrypted)
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            test_resp2 = await http_client.post(
                f"https://{shop_domain}/admin/api/2025-01/graphql.json",
                json={"query": "{ shop { name myshopifyDomain } }"},
                headers={
                    "Content-Type": "application/json",
                    "X-Shopify-Access-Token": access_token,
                },
            )
            sync_result["raw_token_status"] = test_resp2.status_code
            sync_result["raw_token_body"] = test_resp2.text[:300]

    except Exception as e:
        import traceback
        sync_result["status"] = "error"
        sync_result["error"] = str(e)
        sync_result["type"] = type(e).__name__
        sync_result["traceback"] = traceback.format_exc()[-500:]

    return {
        "status": "ok",
        "shop_id": str(shop.id),
        "domain": shop_domain,
        "created": created,
        "scopes": scopes,
        "token_found": True,
        "token_preview": access_token[:8] + "...",
        "sync": sync_result,
    }
