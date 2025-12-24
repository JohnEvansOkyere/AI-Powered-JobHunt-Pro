"""
Request Logging Middleware

Logs all incoming requests and outgoing responses for monitoring and debugging.
Includes timing information and request/response metadata.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.

    Logs:
    - Request method, path, query params
    - Response status code
    - Request duration
    - Client IP (if available)
    - User agent
    """

    # Paths to exclude from logging (to reduce noise)
    EXCLUDE_PATHS = {"/health", "/metrics", "/api/docs", "/api/redoc", "/api/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: The incoming request
            call_next: The next middleware/handler

        Returns:
            Response from the handler
        """
        # Skip logging for excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        # Extract request metadata
        start_time = time.time()
        request_id = getattr(request.state, "request_id", None)

        # Get client IP from headers or direct connection
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP")
            or request.client.host if request.client else "unknown"
        )

        user_agent = request.headers.get("User-Agent", "unknown")

        # Extract query params
        query_params = dict(request.query_params) if request.query_params else {}

        # Log incoming request
        logger.info(
            "incoming_request",
            method=request.method,
            path=request.url.path,
            query_params=query_params if settings.DEBUG else {},
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log failed request
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
                request_id=request_id,
            )
            raise

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        log_level = "info"
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"

        log_method = getattr(logger, log_level)
        log_method(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            client_ip=client_ip,
            request_id=request_id,
        )

        # Add request ID to response headers for debugging
        response.headers["X-Request-ID"] = request_id or "unknown"

        return response
