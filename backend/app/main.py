"""
FastAPI Application Entry Point

This module initializes the FastAPI application with all routes,
middleware, and configuration.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api.v1.router import api_router
from app.middleware import ErrorHandlerMiddleware, RequestLoggingMiddleware
from app.middleware.request_size_limit import RequestSizeLimitMiddleware

logger = get_logger(__name__)


# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Database connection initialization
    - Background task initialization (APScheduler for job scraping)
    - Cleanup on shutdown
    """
    # Startup
    logger.info("🚀 Starting application...")

    # Start the job scraper scheduler
    try:
        from app.scheduler import start_scheduler, stop_scheduler
        scheduler = start_scheduler()
        logger.info("✅ Job scraper scheduler started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start job scraper scheduler: {e}", exc_info=True)
        scheduler = None

    yield

    # Shutdown
    logger.info("🛑 Shutting down application...")
    if scheduler:
        try:
            from app.scheduler import stop_scheduler
            stop_scheduler()
            logger.info("✅ Job scraper scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {e}", exc_info=True)


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application instance.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="AI Job Application Platform API",
        description="Production-ready API for AI-powered job matching and application generation",
        version="1.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS Middleware (First - must be before other middleware to handle OPTIONS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request body size limit (prevent memory exhaustion DoS; 10MB default)
    app.add_middleware(RequestSizeLimitMiddleware)

    # Error Handler Middleware (catches all exceptions)
    app.add_middleware(ErrorHandlerMiddleware)

    # Request Logging Middleware (logs all requests)
    app.add_middleware(RequestLoggingMiddleware)

    # Trusted Host Middleware (production)
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Global exception handler for validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle FastAPI validation errors with detailed logging."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            "validation_error",
            method=request.method,
            path=request.url.path,
            errors=exc.errors(),
            request_id=request_id,
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors() if settings.DEBUG else {},
                    "request_id": request_id,
                }
            }
        )

    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        return {"status": "healthy", "version": "1.0.0"}

    return app


# Create application instance
app = create_application()

