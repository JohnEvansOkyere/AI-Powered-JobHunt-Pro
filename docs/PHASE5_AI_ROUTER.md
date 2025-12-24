# Phase 5: AI Model Router & Integration - Documentation

## Overview

Phase 5 enhances the AI Model Router with cost tracking, rate limiting, usage analytics, and a high-level service layer for common AI operations.

## Status: ✅ Complete

---

## Features Implemented

### 1. Cost Tracking & Analytics

**Location**: `backend/app/ai/usage_tracker.py`

- **Usage Recording**: Tracks every AI API call with:
  - Task type
  - Provider used
  - Input/output tokens
  - Cost in USD
  - Success/failure status
  - Timestamp

- **Statistics**:
  - Total requests (successful/failed)
  - Total tokens (input/output)
  - Cost by provider
  - Cost by task type
  - All-time cost tracking

**Usage**:
```python
from app.ai.usage_tracker import get_usage_tracker

tracker = get_usage_tracker()
stats = tracker.get_usage_stats(hours=24)
print(f"Total cost: ${stats['cost_usd']:.2f}")
```

### 2. Rate Limiting

**Features**:
- Per-user rate limiting (60 requests/minute default)
- Automatic fallback to alternative providers when rate limit exceeded
- Configurable limits per provider

**Implementation**:
- Rate limits checked before each API call
- Automatic provider fallback if limit exceeded
- Thread-safe implementation

### 3. Enhanced AI Router

**Location**: `backend/app/ai/router.py`

**New Features**:
- **Cost Tracking**: Automatic cost calculation and recording
- **Token Estimation**: Uses `tiktoken` for accurate token counting
- **Rate Limiting**: Integrated rate limit checking
- **Cost Optimization**: Option to prefer cheaper providers
- **Better Error Handling**: Improved fallback logic

**Cost Calculation**:
```python
# Automatically calculates cost based on:
# - Input tokens × input cost per 1K tokens
# - Output tokens × output cost per 1K tokens
cost = (input_tokens / 1000) * input_cost + (output_tokens / 1000) * output_cost
```

**Cost Optimization**:
```python
# Use cheaper providers when optimize_cost=True
response = await router.generate(
    task_type=TaskType.FAST_SUMMARY,
    prompt="Summarize this text...",
    optimize_cost=True  # Prefers Groq/Gemini over OpenAI
)
```

### 4. AI Service Layer

**Location**: `backend/app/services/ai_service.py`

High-level service for common AI operations:

- **`parse_cv()`**: Extract structured data from CV text
- **`tailor_cv()`**: Tailor CV for specific job
- **`generate_cover_letter()`**: Generate cover letters
- **`match_jobs()`**: Match CV against job descriptions (placeholder)
- **`get_usage_stats()`**: Get usage statistics
- **`get_provider_stats()`**: Get provider-specific statistics

**Usage**:
```python
from app.services.ai_service import get_ai_service

ai_service = get_ai_service()

# Parse CV
cv_data = await ai_service.parse_cv(cv_text, user_id="user-123")

# Generate cover letter
cover_letter = await ai_service.generate_cover_letter(
    cv_data=cv_data,
    job_description=job_desc,
    company_name="Acme Corp"
)
```

### 5. API Endpoints

**Location**: `backend/app/api/v1/endpoints/ai.py`

**Endpoints**:
- `GET /api/v1/ai/usage?hours=24`: Get usage statistics
- `GET /api/v1/ai/usage/provider/{provider}?hours=24`: Get provider statistics

**Response Example**:
```json
{
  "period_hours": 24,
  "total_requests": 150,
  "successful_requests": 148,
  "failed_requests": 2,
  "total_input_tokens": 45000,
  "total_output_tokens": 12000,
  "total_tokens": 57000,
  "cost_usd": 0.75,
  "cost_by_provider": {
    "openai": 0.50,
    "gemini": 0.25
  },
  "cost_by_task": {
    "cv_parsing": 0.30,
    "cover_letter": 0.45
  },
  "total_cost_all_time": 12.50
}
```

---

## Provider Cost Rankings

Providers are ranked by cost (cheapest first):

1. **Groq**: ~$0.0007 per 1K tokens (very cheap, fast)
2. **Gemini**: ~$0.001 per 1K tokens (cheap, good quality)
3. **Grok**: ~$0.01 per 1K tokens (moderate)
4. **OpenAI (GPT-4 Turbo)**: ~$0.02 per 1K tokens (expensive, best quality)

---

## Task Type Mappings

Default provider for each task type:

- **CV_PARSING**: OpenAI (structured extraction)
- **CV_TAILORING**: OpenAI (high quality)
- **COVER_LETTER**: OpenAI (professional writing)
- **EMAIL_DRAFTING**: Grok (conversational)
- **FAST_SUMMARY**: Groq (speed + cost)
- **JOB_ANALYSIS**: Gemini (analysis tasks)
- **JOB_MATCHING**: Gemini (matching algorithms)

---

## Configuration

### Environment Variables

No new environment variables required. Uses existing:
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `GROK_API_KEY`

### Dependencies

New dependency added:
- `tiktoken==0.5.2` (for accurate token counting)

---

## Usage Examples

### Basic Usage

```python
from app.ai.router import get_model_router
from app.ai.base import TaskType

router = get_model_router()

response = await router.generate(
    task_type=TaskType.CV_PARSING,
    prompt="Extract information from this CV...",
    user_id="user-123"
)
```

### Cost-Optimized Usage

```python
# Use cheaper providers when quality requirements are lower
response = await router.generate(
    task_type=TaskType.FAST_SUMMARY,
    prompt="Summarize this...",
    optimize_cost=True  # Prefers Groq/Gemini
)
```

### Using AI Service

```python
from app.services.ai_service import get_ai_service

ai_service = get_ai_service()

# Parse CV
cv_data = await ai_service.parse_cv(cv_text)

# Generate cover letter
cover_letter = await ai_service.generate_cover_letter(
    cv_data=cv_data,
    job_description=job_desc,
    company_name="Company Name"
)

# Get usage stats
stats = ai_service.get_usage_stats(hours=24)
print(f"Total cost: ${stats['cost_usd']:.2f}")
```

---

## Integration with Existing Code

### CV Parser Integration

The CV parser (`backend/app/services/cv_parser.py`) already uses the router:

```python
from app.ai.router import get_model_router
from app.ai.base import TaskType

router = get_model_router()
response = await router.generate(
    task_type=TaskType.CV_PARSING,
    prompt=prompt,
    max_tokens=2000
)
```

**Automatic Benefits**:
- Cost tracking
- Rate limiting
- Error handling
- Fallback providers

---

## Cost Optimization Strategies

1. **Task-Specific Routing**: Use cheaper providers for less critical tasks
2. **Cost-Aware Selection**: Enable `optimize_cost=True` for non-critical operations
3. **Provider Fallback**: Automatically falls back to cheaper providers if preferred fails
4. **Token Estimation**: Accurate token counting prevents over-spending

---

## Monitoring & Analytics

### View Usage Statistics

```bash
# Get overall usage stats
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/ai/usage?hours=24

# Get provider-specific stats
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/ai/usage/provider/openai?hours=24
```

### Programmatic Access

```python
from app.services.ai_service import get_ai_service

ai_service = get_ai_service()

# Overall stats
stats = ai_service.get_usage_stats(hours=24)

# Provider stats
openai_stats = ai_service.get_provider_stats("openai", hours=24)
```

---

## Error Handling

The router includes comprehensive error handling:

1. **Provider Unavailable**: Falls back to alternative providers
2. **Rate Limit Exceeded**: Automatically tries fallback provider
3. **API Errors**: Logged and tracked, fallback attempted
4. **Token Limits**: Handled gracefully with error messages

---

## Performance Considerations

- **Token Counting**: Uses `tiktoken` for accurate, fast token estimation
- **Thread Safety**: Usage tracker is thread-safe for concurrent requests
- **Memory Management**: Old records automatically cleaned (24-hour window)
- **Lazy Initialization**: Providers initialized only when needed

---

## Future Enhancements

Potential improvements for future phases:

1. **Per-User Cost Tracking**: Track costs per user for billing
2. **Budget Limits**: Set per-user or per-organization budgets
3. **Advanced Matching**: Implement proper job matching algorithm
4. **Streaming Support**: Add streaming responses for better UX
5. **Caching**: Cache common AI responses to reduce costs
6. **A/B Testing**: Test different providers for quality comparison

---

## Testing

### Test Cost Tracking

```python
from app.ai.router import get_model_router
from app.ai.base import TaskType
from app.services.ai_service import get_ai_service

router = get_model_router()
ai_service = get_ai_service()

# Make some API calls
await router.generate(
    task_type=TaskType.FAST_SUMMARY,
    prompt="Test prompt",
    user_id="test-user"
)

# Check stats
stats = ai_service.get_usage_stats(hours=1)
assert stats['total_requests'] > 0
assert stats['cost_usd'] > 0
```

---

## Troubleshooting

### Issue: High Costs

**Solution**: Enable cost optimization:
```python
response = await router.generate(
    task_type=TaskType.FAST_SUMMARY,
    prompt=prompt,
    optimize_cost=True  # Use cheaper providers
)
```

### Issue: Rate Limit Errors

**Solution**: The router automatically falls back to alternative providers. Check usage stats to see which provider is being rate-limited.

### Issue: No Provider Available

**Solution**: Ensure at least one AI provider API key is configured in `.env`.

---

## Summary

Phase 5 successfully enhances the AI Model Router with:

✅ Cost tracking and analytics  
✅ Rate limiting  
✅ Usage statistics API  
✅ High-level AI service layer  
✅ Cost optimization strategies  
✅ Improved error handling  
✅ Token counting with tiktoken  

The system is now production-ready with comprehensive monitoring and cost control capabilities.

