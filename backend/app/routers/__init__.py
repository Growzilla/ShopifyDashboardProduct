"""
API routers package.
"""
from app.routers.code_analysis import router as code_analysis_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.insights import router as insights_router
from app.routers.shops import router as shops_router

__all__ = [
    "health_router",
    "shops_router",
    "insights_router",
    "dashboard_router",
    "code_analysis_router",
]
