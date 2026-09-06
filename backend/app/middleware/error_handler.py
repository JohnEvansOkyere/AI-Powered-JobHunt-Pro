"""
Error Handler Middleware

Centralized error handling for all application exceptions.
Provides consistent error responses and comprehensive logging.
"""

import traceback
import uuid
from typing import Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

from app.core.config import settings
from app.exceptions import AppException

logger = get_logger(__name__)

SERVICE_UNAVAILABLE = "This service is temporarily unavailable. Please try again later."
# Keep the recovery guidance for a password update whose outcome is uncertain.
SAFE_SERVICE_MESSAGES = {
    "Password reset is temporarily unavailable.",
    "Could not confirm the reset. Try signing in with your new password, or request a new code.",
}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException is handled inside FastAPI, before middleware can catch it."""
    detail = exc.detail
    if exc.status_code >= 500:
        logger.error("http_service_error", status_code=exc.status_code,
                     path=request.url.path, request_id=getattr(request.state, "request_id", "unknown"))
        detail = detail if isinstance(detail, str) and detail in SAFE_SERVICE_MESSAGES else SERVICE_UNAVAILABLE
    headers = dict(exc.headers or {})
    headers["Cache-Control"] = "no-store"
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic input/ctx/msg can contain passwords, CVs and exception text.
    errors = [{"loc": error["loc"], "type": error["type"]} for error in exc.errors()]
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("validation_error", method=request.method, path=request.url.path,
                   errors=errors, request_id=request_id)
    return JSONResponse(status_code=422, headers={"Cache-Control": "no-store"}, content={
        "error": {"code": "VALIDATION_ERROR", "message": "Check the details you entered and try again.",
                  "details": {}, "request_id": request_id},
    })


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler middleware.

    Catches all unhandled exceptions and returns consistent JSON responses.
    Logs all errors with request context for debugging.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and catch any exceptions.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response with proper error handling
        """
        # Skip error handling for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Generate unique request ID for tracing
        request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            return response

        except AppException as exc:
            # Handle custom application exceptions
            return await self._handle_app_exception(request, exc, request_id)

        except SQLAlchemyError as exc:
            # Handle database exceptions
            return await self._handle_database_exception(request, exc, request_id)

        except ValueError as exc:
            # Handle value errors (often from parsing)
            return await self._handle_value_error(request, exc, request_id)

        except Exception as exc:
            # Handle all other unexpected exceptions
            return await self._handle_unexpected_exception(request, exc, request_id)

    async def _handle_app_exception(
        self, request: Request, exc: AppException, request_id: str
    ) -> JSONResponse:
        """Handle custom application exceptions."""
        logger.warning(
            "application_exception",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
            method=request.method,
            request_id=request_id,
            details=exc.details,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": SERVICE_UNAVAILABLE if exc.status_code >= 500 else exc.message,
                    "details": {},
                    "request_id": request_id,
                }
            },
        )

    async def _handle_database_exception(
        self, request: Request, exc: SQLAlchemyError, request_id: str
    ) -> JSONResponse:
        """Handle database-related exceptions."""
        error_type = type(exc).__name__

        logger.error(
            "database_exception",
            error_type=error_type,
            error_message=str(exc),
            path=request.url.path,
            method=request.method,
            request_id=request_id,
            traceback=traceback.format_exc() if settings.DEBUG else None,
        )

        # Determine specific error type
        if isinstance(exc, IntegrityError):
            status_code = status.HTTP_409_CONFLICT
            error_code = "DATABASE_INTEGRITY_ERROR"
            message = "This change conflicts with an existing record. Refresh and try again."
        elif isinstance(exc, OperationalError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            error_code = "DATABASE_UNAVAILABLE"
            message = SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_code = "DATABASE_ERROR"
            message = SERVICE_UNAVAILABLE

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": {},
                    "request_id": request_id,
                }
            },
        )

    async def _handle_value_error(
        self, request: Request, exc: ValueError, request_id: str
    ) -> JSONResponse:
        """Handle value errors (parsing, conversion, etc.)."""
        logger.warning(
            "value_error",
            error_message=str(exc),
            path=request.url.path,
            method=request.method,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_VALUE",
                    "message": "Check the details you entered and try again.",
                    "details": {},
                    "request_id": request_id,
                }
            },
        )

    async def _handle_unexpected_exception(
        self, request: Request, exc: Exception, request_id: str
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        error_type = type(exc).__name__

        logger.error(
            "unexpected_exception",
            error_type=error_type,
            error_message=str(exc),
            path=request.url.path,
            method=request.method,
            request_id=request_id,
            traceback=traceback.format_exc(),
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": SERVICE_UNAVAILABLE,
                    "details": {},
                    "request_id": request_id,
                }
            },
        )
