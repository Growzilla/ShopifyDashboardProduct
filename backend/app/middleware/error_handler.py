"""
Global error handling middleware.
"""
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler that catches unhandled exceptions
    and returns proper JSON responses.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(
                "Unhandled exception",
                error=str(e),
                path=request.url.path,
                method=request.method,
            )

            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "type": type(e).__name__,
                },
            )
