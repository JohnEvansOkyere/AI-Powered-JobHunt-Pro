# Error Handling & Logging Guide

## Overview

This document describes the centralized error handling and logging infrastructure implemented in the AI-Powered JobHunt Pro application.

## Table of Contents

1. [Architecture](#architecture)
2. [Custom Exceptions](#custom-exceptions)
3. [Error Handling Middleware](#error-handling-middleware)
4. [Request Logging](#request-logging)
5. [Structured Logging](#structured-logging)
6. [Best Practices](#best-practices)
7. [Examples](#examples)

---

## Architecture

The error handling system consists of three main components:

```
┌─────────────────────────────────────────┐
│         Incoming Request                │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  RequestLoggingMiddleware               │
│  - Generate request_id                  │
│  - Log request details                  │
│  - Track request duration               │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  ErrorHandlerMiddleware                 │
│  - Catch all exceptions                 │
│  - Format error responses               │
│  - Log errors with context              │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Application Logic                 │
│  - Custom exceptions                    │
│  - Business logic                       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Structured Logging                 │
│  - JSON logs (production)               │
│  - Pretty logs (development)            │
│  - Request context tracking             │
└─────────────────────────────────────────┘
```

---

## Custom Exceptions

All custom exceptions inherit from `AppException` and provide structured error information.

### Base Exception

```python
from app.exceptions import AppException

class AppException(Exception):
    """
    Base exception class.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code
        error_code: Machine-readable error code
        details: Additional error context
    """
```

### Available Exceptions

#### 1. DatabaseError (500)
```python
from app.exceptions import DatabaseError

raise DatabaseError(
    message="Failed to insert user record",
    details={"table": "users", "operation": "insert"}
)
```

#### 2. AuthenticationError (401)
```python
from app.exceptions import AuthenticationError

raise AuthenticationError(
    message="Invalid credentials",
    details={"reason": "password_mismatch"}
)
```

#### 3. AuthorizationError (403)
```python
from app.exceptions import AuthorizationError

raise AuthorizationError(
    message="User does not have permission to access this resource"
)
```

#### 4. NotFoundError (404)
```python
from app.exceptions import NotFoundError

raise NotFoundError(
    message="CV not found",
    resource_type="cv",
    resource_id="123"
)
```

#### 5. ValidationError (422)
```python
from app.exceptions import ValidationError

raise ValidationError(
    message="Invalid email format",
    field="email",
    details={"provided": "invalid-email"}
)
```

#### 6. ConflictError (409)
```python
from app.exceptions import ConflictError

raise ConflictError(
    message="Email already registered",
    details={"email": "user@example.com"}
)
```

#### 7. ExternalAPIError (502)
```python
from app.exceptions import ExternalAPIError

raise ExternalAPIError(
    message="OpenAI API request failed",
    service_name="openai",
    details={"error": "rate_limit_exceeded"}
)
```

#### 8. RateLimitError (429)
```python
from app.exceptions import RateLimitError

raise RateLimitError(
    message="Too many requests",
    retry_after=60,
    details={"limit": 100, "window": "1 minute"}
)
```

#### 9. StorageError (500)
```python
from app.exceptions import StorageError

raise StorageError(
    message="Failed to upload file to Supabase",
    operation="upload",
    details={"bucket": "cvs", "filename": "resume.pdf"}
)
```

#### 10. AIServiceError (503)
```python
from app.exceptions import AIServiceError

raise AIServiceError(
    message="AI model inference failed",
    provider="openai",
    details={"model": "gpt-4", "error": "timeout"}
)
```

#### 11. InvalidConfigurationError (500)
```python
from app.exceptions import InvalidConfigurationError

raise InvalidConfigurationError(
    message="Missing required environment variable",
    config_key="OPENAI_API_KEY"
)
```

---

## Error Handling Middleware

The `ErrorHandlerMiddleware` catches all unhandled exceptions and returns consistent error responses.

### Error Response Format

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {},
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Automatic Error Handling

The middleware automatically handles:

1. **Custom Application Exceptions** (`AppException`)
   - Returns appropriate status code
   - Logs at WARNING level
   - Includes structured error details

2. **Database Exceptions** (`SQLAlchemyError`)
   - Integrity errors (409 Conflict)
   - Operational errors (503 Service Unavailable)
   - Generic database errors (500 Internal Server Error)
   - Logs at ERROR level with traceback in debug mode

3. **Value Errors** (`ValueError`)
   - Returns 400 Bad Request
   - Logs at WARNING level

4. **Unexpected Exceptions**
   - Returns 500 Internal Server Error
   - Logs at ERROR level with full traceback
   - Hides details in production

---

## Request Logging

The `RequestLoggingMiddleware` logs all HTTP requests and responses.

### Logged Information

**For all requests:**
- HTTP method
- Request path
- Query parameters (in debug mode)
- Client IP address
- User agent
- Request ID (UUID)

**For all responses:**
- Status code
- Request duration (milliseconds)
- Request ID (also added to response headers as `X-Request-ID`)

### Excluded Paths

The following paths are excluded from logging to reduce noise:
- `/health`
- `/metrics`
- `/api/docs`
- `/api/redoc`
- `/api/openapi.json`

### Log Levels

- `INFO`: Successful requests (2xx, 3xx)
- `WARNING`: Client errors (4xx)
- `ERROR`: Server errors (5xx)

---

## Structured Logging

The application uses `structlog` for structured logging with JSON output in production and pretty-printed logs in development.

### Basic Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("user_logged_in", user_id="123")

# Log with multiple fields
logger.warning(
    "rate_limit_approaching",
    user_id="123",
    current_count=95,
    limit=100,
    window="1m"
)

# Error logging
logger.error(
    "payment_failed",
    user_id="123",
    amount=99.99,
    error="insufficient_funds"
)
```

### Request Context Binding

Add context that automatically appears in all subsequent logs within the same request:

```python
from app.core.logging import bind_request_context, get_logger

logger = get_logger(__name__)

async def process_cv(cv_id: str, user_id: str):
    # Bind context for this request
    bind_request_context(cv_id=cv_id, user_id=user_id)

    # All subsequent logs will include cv_id and user_id
    logger.info("starting_cv_processing")
    # ... process cv ...
    logger.info("cv_processing_complete")
    # Both logs will include cv_id and user_id
```

### Logger Context Manager

For temporary context that should be cleaned up:

```python
from app.core.logging import LoggerContext, get_logger

logger = get_logger(__name__)

def analyze_resume(file_path: str):
    with LoggerContext(file_path=file_path, operation="resume_analysis"):
        logger.info("starting_analysis")  # Includes file_path and operation
        # ... analyze resume ...
        logger.info("analysis_complete")  # Includes file_path and operation
    # Context is automatically cleaned up here
```

### Log Output

**Development (pretty-printed):**
```
2025-01-15T10:30:45.123Z [info     ] user_logged_in user_id=123 request_id=550e8400-e29b-41d4-a716-446655440000
```

**Production (JSON):**
```json
{
  "event": "user_logged_in",
  "level": "info",
  "timestamp": "2025-01-15T10:30:45.123Z",
  "user_id": "123",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "logger": "app.api.v1.endpoints.auth"
}
```

---

## Best Practices

### 1. Use Specific Exceptions

❌ **Bad:**
```python
raise Exception("CV not found")
```

✅ **Good:**
```python
from app.exceptions import NotFoundError

raise NotFoundError(
    message="CV not found",
    resource_type="cv",
    resource_id=cv_id
)
```

### 2. Include Contextual Details

❌ **Bad:**
```python
raise DatabaseError("Query failed")
```

✅ **Good:**
```python
raise DatabaseError(
    message="Failed to retrieve user CVs",
    details={
        "user_id": user_id,
        "query": "SELECT * FROM cvs WHERE user_id = ?",
        "error": str(e)
    }
)
```

### 3. Log Before Raising (for important errors)

```python
from app.core.logging import get_logger
from app.exceptions import ExternalAPIError

logger = get_logger(__name__)

try:
    response = await openai_client.chat.completions.create(...)
except Exception as e:
    logger.error(
        "openai_request_failed",
        model="gpt-4",
        error=str(e),
        user_id=user_id
    )
    raise ExternalAPIError(
        message="Failed to generate AI response",
        service_name="openai",
        details={"model": "gpt-4", "error": str(e)}
    )
```

### 4. Use Structured Logging

❌ **Bad:**
```python
logger.info(f"User {user_id} uploaded CV {cv_id}")
```

✅ **Good:**
```python
logger.info("cv_uploaded", user_id=user_id, cv_id=cv_id, filename=filename)
```

### 5. Add Request Context for Complex Operations

```python
from app.core.logging import bind_request_context

async def scrape_jobs(job_board: str, query: str):
    bind_request_context(
        operation="job_scraping",
        job_board=job_board,
        query=query
    )

    # All logs in this function will include the context
    logger.info("starting_scrape")
    # ... scraping logic ...
    logger.info("scrape_completed", jobs_found=len(jobs))
```

### 6. Handle External API Errors Gracefully

```python
from app.exceptions import ExternalAPIError

async def call_external_api():
    try:
        response = await external_service.call()
    except httpx.HTTPStatusError as e:
        raise ExternalAPIError(
            message=f"External API returned {e.response.status_code}",
            service_name="external_service",
            details={
                "status_code": e.response.status_code,
                "response": e.response.text[:500]
            }
        )
    except httpx.TimeoutException:
        raise ExternalAPIError(
            message="External API request timed out",
            service_name="external_service"
        )
```

---

## Examples

### Example 1: Endpoint with Error Handling

```python
from fastapi import APIRouter, Depends
from app.core.logging import get_logger, bind_request_context
from app.exceptions import NotFoundError, DatabaseError

router = APIRouter()
logger = get_logger(__name__)

@router.get("/cvs/{cv_id}")
async def get_cv(cv_id: str, user_id: str = Depends(get_current_user)):
    # Add request context
    bind_request_context(cv_id=cv_id, user_id=user_id)

    logger.info("fetching_cv")

    try:
        cv = await db.get_cv(cv_id, user_id)
    except SQLAlchemyError as e:
        raise DatabaseError(
            message="Failed to fetch CV from database",
            details={"cv_id": cv_id}
        )

    if not cv:
        raise NotFoundError(
            message="CV not found",
            resource_type="cv",
            resource_id=cv_id
        )

    logger.info("cv_fetched_successfully")
    return cv
```

### Example 2: Service Layer with Comprehensive Error Handling

```python
from app.core.logging import get_logger, LoggerContext
from app.exceptions import StorageError, ValidationError

logger = get_logger(__name__)

class CVService:
    async def upload_cv(self, file: UploadFile, user_id: str) -> str:
        with LoggerContext(operation="cv_upload", user_id=user_id, filename=file.filename):
            # Validate file
            if not file.filename.endswith(('.pdf', '.docx')):
                raise ValidationError(
                    message="Invalid file format. Only PDF and DOCX are supported",
                    field="file",
                    details={"filename": file.filename}
                )

            logger.info("uploading_to_storage")

            # Upload to Supabase
            try:
                file_path = await supabase.storage.upload(file)
            except Exception as e:
                logger.error("storage_upload_failed", error=str(e))
                raise StorageError(
                    message="Failed to upload file to storage",
                    operation="upload",
                    details={"filename": file.filename, "error": str(e)}
                )

            logger.info("cv_uploaded_successfully", file_path=file_path)
            return file_path
```

### Example 3: Background Task Error Handling

```python
from celery import shared_task
from app.core.logging import get_logger, bind_request_context
from app.exceptions import ExternalAPIError

logger = get_logger(__name__)

@shared_task(bind=True, max_retries=3)
def scrape_jobs(self, job_board: str, query: str):
    task_id = self.request.id
    bind_request_context(task_id=task_id, job_board=job_board)

    logger.info("starting_job_scraping")

    try:
        jobs = scraper.scrape(job_board, query)
        logger.info("scraping_completed", jobs_found=len(jobs))
        return jobs
    except ExternalAPIError as e:
        logger.warning("scraping_failed_retrying", attempt=self.request.retries)
        raise self.retry(exc=e, countdown=60)
    except Exception as e:
        logger.error("scraping_failed_permanently", error=str(e))
        raise
```

---

## Testing Error Handling

### Test Custom Exceptions

```python
from app.exceptions import NotFoundError

def test_not_found_error():
    with pytest.raises(NotFoundError) as exc_info:
        raise NotFoundError(
            message="Resource not found",
            resource_type="cv",
            resource_id="123"
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "NOT_FOUND"
    assert exc_info.value.details["resource_id"] == "123"
```

### Test Error Responses

```python
def test_cv_not_found_response(client, auth_headers):
    response = client.get("/api/v1/cvs/nonexistent", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert "request_id" in response.json()["error"]
```

---

## Monitoring and Observability

### Request Tracking

Every request gets a unique `request_id` that is:
1. Generated by the middleware
2. Included in all log entries
3. Returned in the `X-Request-ID` response header
4. Included in all error responses

Use this ID to trace a request through all logs:

```bash
# Filter logs by request ID
grep "550e8400-e29b-41d4-a716-446655440000" application.log
```

### Error Analytics

In production, all errors are logged with:
- Error type and code
- Request path and method
- User context (if available)
- Request ID for tracing
- Timestamp

This enables you to:
- Track error rates by endpoint
- Identify common failure patterns
- Debug production issues with request IDs
- Monitor external service failures

---

## Next Steps

1. **Set up Sentry** - For real-time error monitoring and alerting
2. **Add Rate Limiting** - Prevent abuse and DDoS
3. **Implement Metrics** - Track request counts, latencies, error rates
4. **Create Alerts** - Set up automated alerts for critical errors

---

## Support

For questions or issues with error handling:
- Check logs with structured search
- Use request IDs to trace issues
- Review this guide for best practices
- Consult the team for complex scenarios
