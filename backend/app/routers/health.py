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
