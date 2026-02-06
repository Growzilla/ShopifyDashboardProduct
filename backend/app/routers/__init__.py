"""
API routers package.

MVP SIMPLIFICATION: Code analysis router commented out - not core value proposition.
To re-enable: uncomment the code_analysis imports and add back to __all__.
"""
# from app.routers.code_analysis import router as code_analysis_router  # COMMENTED OUT FOR MVP
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.insights import router as insights_router
from app.routers.shops import router as shops_router

__all__ = [
    "health_router",
    "shops_router",
    "insights_router",
    "dashboard_router",
    # "code_analysis_router",  # COMMENTED OUT FOR MVP
]
