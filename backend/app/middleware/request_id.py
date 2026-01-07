"""
Request ID middleware for tracing.
"""
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Adds a unique request ID to each request for tracing.
    The ID is added to response headers and logging context.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Get request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Add to logging context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Store in request state for access in handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response
