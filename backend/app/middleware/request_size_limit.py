"""
Request body size limit middleware.

Rejects oversized Content-Length requests and explicit chunked request bodies.
The application expects bounded JSON/form uploads; accepting chunked bodies would
bypass the Content-Length guard and can exhaust worker memory.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MAX_BODY_BYTES = 10 * 1024 * 1024


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests that bypass or exceed the configured body size limit."""

    def __init__(self, app, max_size: int = None):
        super().__init__(app)
        self.max_size = max_size or getattr(
            settings, "MAX_REQUEST_BODY_BYTES", DEFAULT_MAX_BODY_BYTES
        )

    async def dispatch(self, request: Request, call_next):
        transfer_encoding = request.headers.get("transfer-encoding", "").lower()
        if "chunked" in transfer_encoding:
            logger.warning(
                "chunked_request_body_rejected",
                path=request.url.path,
                max_allowed=self.max_size,
            )
            return self._error_response(
                status_code=411,
                code="LENGTH_REQUIRED",
                message="Chunked request bodies are not accepted. Send Content-Length.",
            )

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
                    return self._error_response(
                        status_code=413,
                        code="REQUEST_ENTITY_TOO_LARGE",
                        message=f"Request body too large (max {self.max_size // (1024*1024)}MB)",
                    )
            except ValueError:
                return self._error_response(
                    status_code=400,
                    code="INVALID_CONTENT_LENGTH",
                    message="Invalid Content-Length header.",
                )

        return await call_next(request)

    def _error_response(self, *, status_code: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                }
            },
        )
