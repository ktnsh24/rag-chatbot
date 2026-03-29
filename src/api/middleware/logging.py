"""
Request Logging Middleware

Logs every HTTP request with:
    - Method, path, status code
    - Processing time (latency)
    - Request ID for tracing

Similar to BnaEventMiddleware in the shared-proxy project.
"""

import time
from uuid import uuid4

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every request.

    Execution order:
        1. Request comes in → this middleware runs FIRST
        2. Logs the incoming request (method, path)
        3. Calls the next handler (the actual route)
        4. Logs the response (status code, latency)

    Why middleware instead of decorators on each route?
        - DRY: you don't repeat logging code in every route
        - Consistent: every request gets logged, even if you forget
        - Centralized: one place to change logging format
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid4())
        start_time = time.time()

        # Attach request_id to request state (accessible in route handlers)
        request.state.request_id = request_id

        # Log incoming request
        logger.info(f"[{request_id}] → {request.method} {request.url.path}")

        # Process the request
        response = await call_next(request)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Log response
        logger.info(f"[{request_id}] ← {response.status_code} ({latency_ms}ms)")

        # Add tracing headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Latency-Ms"] = str(latency_ms)

        return response
