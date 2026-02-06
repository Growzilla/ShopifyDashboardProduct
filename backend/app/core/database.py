"""
Database connection management with SQLAlchemy async.
Provides session dependency injection and connection pooling.

For MVP development, database is optional - endpoints fall back to demo data.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Flag to track if database is available
_db_available: bool = False


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


def create_engine() -> AsyncEngine:
    """Create async database engine with proper configuration."""
    # Convert postgresql:// to postgresql+asyncpg://
    database_url = str(settings.database_url)
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Log the sanitized URL for debugging (hide password)
    import re
    sanitized = re.sub(r':([^:@]+)@', ':***@', database_url)
    print(f"[DATABASE] Connecting to: {sanitized}")

    return create_async_engine(
        database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.database_echo,
        pool_pre_ping=True,  # Verify connections before use
    )


# Global engine and session factory
engine = create_engine()
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    Dependency that provides a database session with automatic cleanup.

    For MVP development, returns None if database is not available,
    allowing endpoints to fall back to demo data.
    """
    if not _db_available:
        yield None
        return

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of request context."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize database tables.

    For MVP development, this is optional - if database connection fails,
    the app continues with demo data fallbacks.
    """
    global _db_available
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _db_available = True
        logger.info("Database initialized")
    except Exception as e:
        _db_available = False
        logger.warning(
            "Database connection failed - running in demo mode",
            error=str(e),
        )


def is_db_available() -> bool:
    """Check if database is available."""
    return _db_available


async def close_db() -> None:
    """Close database connections."""
    if _db_available:
        await engine.dispose()
        logger.info("Database connections closed")
    else:
        logger.info("No database connections to close (demo mode)")
