# Error Handling Quick Start

## Installation Complete ✅

Your centralized error handling and logging system is now fully configured!

## Quick Reference

### Raise Custom Exceptions

```python
from app.exceptions import NotFoundError, ValidationError, ExternalAPIError

# Not found
raise NotFoundError(message="CV not found", resource_type="cv", resource_id="123")

# Validation error
raise ValidationError(message="Invalid email", field="email")

# External API error
raise ExternalAPIError(message="OpenAI timeout", service_name="openai")
```

### Structured Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("user_action", user_id="123", action="upload_cv")

# With context
logger.error("operation_failed", error="timeout", retry_count=3)
```

### Add Request Context

```python
from app.core.logging import bind_request_context

bind_request_context(user_id=user_id, cv_id=cv_id)
# All subsequent logs will include user_id and cv_id
```

## Available Exceptions

| Exception | Status | Use Case |
|-----------|--------|----------|
| `DatabaseError` | 500 | Database operation failures |
| `AuthenticationError` | 401 | Invalid credentials |
| `AuthorizationError` | 403 | Permission denied |
| `NotFoundError` | 404 | Resource not found |
| `ValidationError` | 422 | Invalid input data |
| `ConflictError` | 409 | Resource conflict (duplicate) |
| `ExternalAPIError` | 502 | External service failures |
| `RateLimitError` | 429 | Rate limit exceeded |
| `StorageError` | 500 | File storage failures |
| `AIServiceError` | 503 | AI provider errors |

## Error Response Format

All errors return consistent JSON:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {},
    "request_id": "uuid-here"
  }
}
```

## Middleware Stack

1. **ErrorHandlerMiddleware** - Catches all exceptions
2. **RequestLoggingMiddleware** - Logs all requests with timing
3. **CORSMiddleware** - CORS handling
4. **TrustedHostMiddleware** - Host validation (production)

## Features

✅ Automatic request ID generation
✅ Structured JSON logging (production)
✅ Pretty logs (development)
✅ Request/response logging with timing
✅ Consistent error responses
✅ Context-aware logging
✅ Database error handling
✅ External API error handling
✅ Validation error handling

## Example: Complete Endpoint

```python
from fastapi import APIRouter, Depends
from app.core.logging import get_logger, bind_request_context
from app.exceptions import NotFoundError

router = APIRouter()
logger = get_logger(__name__)

@router.get("/cvs/{cv_id}")
async def get_cv(cv_id: str, user_id: str = Depends(get_current_user)):
    bind_request_context(cv_id=cv_id, user_id=user_id)

    logger.info("fetching_cv")

    cv = await db.get_cv(cv_id)
    if not cv:
        raise NotFoundError(
            message="CV not found",
            resource_type="cv",
            resource_id=cv_id
        )

    logger.info("cv_fetched")
    return cv
```

## Testing

```bash
# Run application
uvicorn app.main:app --reload

# Trigger an error
curl http://localhost:8000/api/v1/cvs/nonexistent \
  -H "Authorization: Bearer token"

# Response
{
  "error": {
    "code": "NOT_FOUND",
    "message": "CV not found",
    "details": {
      "resource_type": "cv",
      "resource_id": "nonexistent"
    },
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Log Examples

**Development (Pretty):**
```
2025-12-23T22:35:00.123Z [info     ] incoming_request method=GET path=/api/v1/cvs/123 request_id=550e8400
2025-12-23T22:35:00.145Z [info     ] fetching_cv cv_id=123 user_id=456
2025-12-23T22:35:00.167Z [info     ] request_completed status_code=200 duration_ms=44.2
```

**Production (JSON):**
```json
{"event":"incoming_request","method":"GET","path":"/api/v1/cvs/123","request_id":"550e8400","timestamp":"2025-12-23T22:35:00.123Z","level":"info"}
{"event":"fetching_cv","cv_id":"123","user_id":"456","request_id":"550e8400","timestamp":"2025-12-23T22:35:00.145Z","level":"info"}
{"event":"request_completed","status_code":200,"duration_ms":44.2,"request_id":"550e8400","timestamp":"2025-12-23T22:35:00.167Z","level":"info"}
```

## Request Tracing

Every request gets a unique ID that appears in:
- All log entries
- Error responses
- Response headers (`X-Request-ID`)

Use it to trace requests through logs:
```bash
grep "550e8400" logs/app.log
```

## Next Steps

1. ✅ Error handling implemented
2. ⏳ Set up Sentry for monitoring
3. ⏳ Add rate limiting
4. ⏳ Implement metrics collection

## Documentation

- **Full Guide**: [ERROR_HANDLING_GUIDE.md](ERROR_HANDLING_GUIDE.md)
- **Examples**: See guide for comprehensive examples
- **Testing**: Integration tests coming soon

---

**Ready to handle errors like a pro!** 🚀
