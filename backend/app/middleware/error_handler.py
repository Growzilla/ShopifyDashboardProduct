"""
Global error handling middleware.

Uses pure ASGI middleware (not BaseHTTPMiddleware) to avoid breaking
async generator dependencies like get_db_session().
"""
import json

from fastapi import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware:
    """
    Pure ASGI error handler that catches unhandled exceptions
    and returns proper JSON 500 responses.

    Does NOT catch HTTPException — those are handled by FastAPI's
    default exception handler and must pass through unchanged.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False
        original_send = send

        async def send_wrapper(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await original_send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Don't intercept HTTPException — let FastAPI handle it
            if isinstance(e, HTTPException):
                raise

            # Only handle truly unhandled exceptions
            if response_started:
                # Headers already sent, can't change the response
                logger.exception(
                    "Unhandled exception after response started",
                    error=str(e),
                    path=scope.get("path", "unknown"),
                )
                raise

            logger.exception(
                "Unhandled exception",
                error=str(e),
                path=scope.get("path", "unknown"),
            )

            # Return JSON 500 error
            body = json.dumps({
                "detail": "Internal server error",
                "type": type(e).__name__,
            }).encode("utf-8")

            await original_send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode()],
                ],
            })
            await original_send({
                "type": "http.response.body",
                "body": body,
            })
