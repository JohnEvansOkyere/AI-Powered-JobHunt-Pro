"""
Custom Exceptions Module

This module defines custom exception classes for different error scenarios
in the application. Each exception provides context and structured error details.
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """
    Base exception class for all application exceptions.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code to return
        error_code: Machine-readable error code
        details: Additional error context
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(AppException):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details,
        )


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(AppException):
    """Raised when user lacks permission for an operation."""

    def __init__(
        self,
        message: str = "Access denied",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details,
        )


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id

        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=error_details,
        )


class ValidationError(AppException):
    """Raised when request data validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=error_details,
        )


class ConflictError(AppException):
    """Raised when an operation conflicts with existing state."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT_ERROR",
            details=details,
        )


class ExternalAPIError(AppException):
    """Raised when an external API call fails."""

    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if service_name:
            error_details["service"] = service_name

        super().__init__(
            message=message,
            status_code=502,
            error_code="EXTERNAL_API_ERROR",
            details=error_details,
        )


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_ERROR",
            details=error_details,
        )


class StorageError(AppException):
    """Raised when file storage operations fail."""

    def __init__(
        self,
        message: str = "Storage operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation

        super().__init__(
            message=message,
            status_code=500,
            error_code="STORAGE_ERROR",
            details=error_details,
        )


class AIServiceError(AppException):
    """Raised when AI service operations fail."""

    def __init__(
        self,
        message: str = "AI service error",
        provider: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if provider:
            error_details["provider"] = provider

        super().__init__(
            message=message,
            status_code=503,
            error_code="AI_SERVICE_ERROR",
            details=error_details,
        )


class InvalidConfigurationError(AppException):
    """Raised when application configuration is invalid."""

    def __init__(
        self,
        message: str = "Invalid configuration",
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key

        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            details=error_details,
        )
