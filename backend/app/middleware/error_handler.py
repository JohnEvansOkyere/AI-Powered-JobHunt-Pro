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
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

from app.core.config import settings
from app.exceptions import AppException

logger = get_logger(__name__)


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
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
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
                    "message": exc.message,
                    "details": exc.details if settings.DEBUG else {},
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
            message = "Database integrity constraint violated"
        elif isinstance(exc, OperationalError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            error_code = "DATABASE_UNAVAILABLE"
            message = "Database service unavailable"
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_code = "DATABASE_ERROR"
            message = "Database operation failed"

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": {"error_type": error_type} if settings.DEBUG else {},
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
                    "message": str(exc) if settings.DEBUG else "Invalid value provided",
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

        # In production, hide detailed error information
        if settings.is_production:
            message = "An unexpected error occurred. Please contact support."
            details = {}
        else:
            message = f"{error_type}: {str(exc)}"
            details = {
                "error_type": error_type,
                "traceback": traceback.format_exc(),
            }

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": message,
                    "details": details,
                    "request_id": request_id,
                }
            },
        )
