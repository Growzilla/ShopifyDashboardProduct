"""
EcomDash V2 API - Main Application Entry Point.

A superior, modular FastAPI application for Shopify AI analytics.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logging import configure_logging, get_logger
from app.middleware import ErrorHandlerMiddleware, RequestIdMiddleware
from app.routers import (
    # code_analysis_router,  # COMMENTED OUT FOR MVP - Overengineered feature
    dashboard_router,
    health_router,
    insights_router,
    shops_router,
)
# from app.routers.analytics import router as analytics_router  # COMMENTED OUT FOR MVP - Overengineered feature

# Configure logging before anything else
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "Starting application",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Initialize database
    await init_db()

    # Initialize Sentry if configured
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_db()


def create_app() -> FastAPI:
    """
    Application factory function.
    Creates and configures the FastAPI application.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered Shopify analytics dashboard API",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Add middleware (order matters - first added = outermost)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestIdMiddleware)

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

    # Register routers
    app.include_router(health_router)
    app.include_router(shops_router, prefix="/api")
    app.include_router(insights_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    # COMMENTED OUT FOR MVP - Overengineered features:
    # app.include_router(code_analysis_router, prefix="/api")  # Code analysis feature - not core value
    # app.include_router(analytics_router)  # Full analytics suite - overkill for MVP

    logger.info(
        "Application created",
        routes=len(app.routes),
        cors_origins=len(settings.allowed_origins),
    )

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
