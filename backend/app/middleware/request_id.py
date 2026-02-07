"""
Request ID middleware for tracing.

Uses pure ASGI middleware (not BaseHTTPMiddleware) to avoid breaking
async generator dependencies like get_db_session().
"""
import uuid

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send


class RequestIdMiddleware:
    """
    Pure ASGI middleware that adds a unique request ID to each request.
    The ID is added to response headers and logging context.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get request ID from headers or generate new one
        request_id = None
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"x-request-id":
                request_id = header_value.decode("utf-8")
                break

        if not request_id:
            request_id = str(uuid.uuid4())

        # Bind to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Inject request_id into scope state for handler access
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append([b"x-request-id", request_id.encode("utf-8")])
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_request_id)
