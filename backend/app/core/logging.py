"""
Logging Configuration

Structured logging setup using structlog for better observability.
Includes request context binding and custom processors.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings

# Context variable for request-scoped logging context
_request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Uses structlog for JSON-formatted logs in production,
    and human-readable logs in development.

    Features:
    - Request ID tracking
    - Environment-based log levels
    - JSON logs in production, pretty logs in development
    - Automatic exception formatting
    - Context variable support for request-scoped data
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Configure structlog
    structlog.configure(
        processors=[
            # Merge context variables (like request_id)
            structlog.contextvars.merge_contextvars,
            # Add custom request context
            add_request_context,
            # Filter by log level
            structlog.stdlib.filter_by_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add log level
            structlog.stdlib.add_log_level,
            # Format positional args
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add stack info if available
            structlog.processors.StackInfoRenderer(),
            # Format exception info
            structlog.processors.format_exc_info,
            # Decode unicode
            structlog.processors.UnicodeDecoder(),
            # Final renderer (JSON for prod, pretty for dev)
            structlog.processors.JSONRenderer()
            if settings.is_production
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def add_request_context(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add request context to log entries.

    Custom processor that adds request-scoped context to all log entries
    within the same request.

    Args:
        logger: The logger instance
        method_name: The name of the log method called
        event_dict: The event dictionary to be logged

    Returns:
        Modified event dictionary with request context
    """
    context = _request_context.get()
    if context:
        event_dict.update(context)
    return event_dict


def bind_request_context(**kwargs: Any) -> None:
    """
    Bind context data to the current request.

    This data will be automatically included in all log entries
    for the current request/async context.

    Example:
        bind_request_context(user_id="123", request_id="abc")
        logger.info("user_action")  # Will include user_id and request_id

    Args:
        **kwargs: Key-value pairs to add to request context
    """
    current_context = _request_context.get()
    updated_context = {**current_context, **kwargs}
    _request_context.set(updated_context)


def clear_request_context() -> None:
    """Clear all request context data."""
    _request_context.set({})


def get_logger(name: str = __name__) -> Any:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance configured with structlog
    """
    return structlog.get_logger(name)


class LoggerContext:
    """
    Context manager for temporary logging context.

    Example:
        with LoggerContext(user_id="123", action="upload"):
            logger.info("processing_file")  # Will include user_id and action
        # Context is automatically cleaned up after the block
    """

    def __init__(self, **kwargs: Any):
        """
        Initialize context manager.

        Args:
            **kwargs: Context data to bind
        """
        self.context = kwargs
        self.previous_context: Optional[Dict[str, Any]] = None

    def __enter__(self) -> "LoggerContext":
        """Enter context and bind data."""
        self.previous_context = _request_context.get()
        bind_request_context(**self.context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore previous state."""
        if self.previous_context is not None:
            _request_context.set(self.previous_context)
        else:
            clear_request_context()
