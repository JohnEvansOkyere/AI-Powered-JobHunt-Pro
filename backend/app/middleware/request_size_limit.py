"""
Request Body Size Limit Middleware

Rejects requests with body larger than max_size to prevent memory exhaustion DoS.
Checks Content-Length header; requests without it (e.g. chunked) are allowed through.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default 10MB (audit recommendation)
DEFAULT_MAX_BODY_BYTES = 10 * 1024 * 1024


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with Content-Length exceeding max_size."""

    def __init__(self, app, max_size: int = None):
        super().__init__(app)
        self.max_size = max_size or getattr(
            settings, "MAX_REQUEST_BODY_BYTES", DEFAULT_MAX_BODY_BYTES
        )

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    logger.warning(
                        "request_body_too_large",
                        content_length=size,
                        max_allowed=self.max_size,
                        path=request.url.path,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "REQUEST_ENTITY_TOO_LARGE",
                                "message": f"Request body too large (max {self.max_size // (1024*1024)}MB)",
                            }
                        },
                    )
            except ValueError:
                pass  # Invalid Content-Length; let downstream handle
        return await call_next(request)
