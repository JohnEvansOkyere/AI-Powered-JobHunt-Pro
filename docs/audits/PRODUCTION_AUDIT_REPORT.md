# AI-Powered JobHunt Pro - Production Audit Report

**Audit Date:** January 30, 2026
**Auditor:** Claude (AI Code Auditor)
**System Version:** 1.0.0
**Purpose:** Pre-release audit for public deployment

**Fixes applied (post-audit):**
- **1.1 Rate limiting:** Per-user rate limiting implemented; `UsageRecord` and `record_usage()` include `user_id`; `check_rate_limit()` counts per user per provider. Router passes `user_id` to `record_usage()` and uses `AI_RATE_LIMIT_PER_MINUTE` per user.
- **1.3 Sanitization:** Sanitizer applied to all AI inputs: `ai_service.py` (parse_cv, tailor_cv, generate_cover_letter), `ai_job_matcher.py` (get_embedding), `external_job_parser.py` (_parse_with_ai). CV/job/cover-letter generators already used sanitizer.
- **1.4 OpenAI key:** Missing key no longer crashes app; `ai_job_matcher` initializes with `client=None` and `_available=False`, returns empty matches when key missing. Config has `is_openai_configured` helper.
- **2.1 Request size:** `RequestSizeLimitMiddleware` added (10MB default); rejects requests with `Content-Length` > limit (413).
- **2.2 Error responses:** Tracebacks never sent to clients; only `error_type` in details when DEBUG; traceback logged only.
- **2.3 Search:** Search query `q` trimmed and limited to 100 chars before use.
- **2.4 Scraping:** `max_results_per_source` validated with `Field(ge=1, le=100)`.
- CSRF left out per request.

---

## Executive Summary

This audit evaluates the AI-Powered JobHunt Pro system for production readiness, focusing on:
- Security vulnerabilities
- Scalability for large candidate volumes
- AI component integrity
- Code quality and reliability

### Overall Assessment: **CONDITIONAL PASS**

The system demonstrates solid architecture and good security practices. However, several **CRITICAL** and **HIGH** severity issues must be addressed before public release.

---

## 1. CRITICAL ISSUES (Must Fix Before Release)

### 1.1 Rate Limiting Not Per-User (Severity: CRITICAL)

**File:** [usage_tracker.py:96-128](backend/app/ai/usage_tracker.py#L96-L128)

**Issue:** The rate limiting implementation tracks requests globally, not per-user. A single malicious user could exhaust the entire system's AI quota.

```python
# Current implementation (PROBLEMATIC)
recent_requests = [
    r for r in self.records
    if r.timestamp > window_start
    and r.provider == provider
]
# TODO comment in code: "For now, we don't track per-user, so use global limit"
```

**Risk:** Denial of service to all users; excessive AI API costs from abuse.

**Recommendation:**
- Implement per-user rate limiting in the UsageRecord dataclass
- Add user_id to usage tracking
- Consider Redis-based distributed rate limiting for production

---

### 1.2 In-Memory Usage Tracking Not Persistent (Severity: CRITICAL)

**File:** [usage_tracker.py:40-41](backend/app/ai/usage_tracker.py#L40-L41)

**Issue:** Usage records are stored in memory (`self.records: list[UsageRecord] = []`). Server restarts lose all usage history, breaking rate limiting and cost tracking.

```python
class UsageTracker:
    def __init__(self):
        self.records: list[UsageRecord] = []  # Lost on restart!
        self.lock = Lock()
```

**Risk:** Rate limits reset on every deployment; billing/cost tracking inaccurate.

**Recommendation:**
- Store usage records in PostgreSQL or Redis
- Implement persistent rate limiting with Redis INCR/EXPIRE

---

### 1.3 Missing Input Sanitization on AI Endpoints (Severity: CRITICAL)

**File:** [ai_service.py](backend/app/services/ai_service.py)

**Issue:** The sanitizer utility exists ([sanitizer.py](backend/app/utils/sanitizer.py)) but is NOT consistently applied to all AI inputs. Job descriptions and user content can contain prompt injection attacks.

**Files Missing Sanitization:**
- `ai_service.py` - CV parsing, cover letter generation
- `cv_generator.py` - CV tailoring
- `cover_letter_generator.py` - Cover letter generation
- `ai_job_matcher.py` - Profile/CV text embedding

**Risk:** Prompt injection attacks could manipulate AI outputs, leak system prompts, or generate malicious content.

**Recommendation:**
- Apply `get_sanitizer().sanitize_text()` to ALL user-provided content before AI processing
- Add `check_injection=True` for all job descriptions

---

### 1.4 Missing OpenAI API Key Validation (Severity: HIGH)

**File:** [ai_job_matcher.py:48-57](backend/app/services/ai_job_matcher.py#L48-L57)

**Issue:** If `OPENAI_API_KEY` is missing, the system raises an exception at initialization, crashing the application.

```python
if not api_key:
    logger.warning("OPENAI_API_KEY not configured - AI matching will fail")
    raise ValueError("OPENAI_API_KEY not found in environment...")
```

**Risk:** Application crash on startup if any AI key is missing.

**Recommendation:**
- Implement graceful degradation
- Return empty matches instead of crashing
- Add health check for AI provider availability

---

## 2. HIGH SEVERITY ISSUES

### 2.1 No Request Body Size Limits (Severity: HIGH)

**File:** [main.py](backend/app/main.py)

**Issue:** No middleware limits the size of request bodies. Large payloads could cause memory exhaustion.

**Risk:** Memory exhaustion DoS attacks.

**Recommendation:**
```python
from starlette.middleware.base import BaseHTTPMiddleware

class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size
```

---

### 2.2 Sensitive Data in Error Responses (Severity: HIGH)

**File:** [error_handler.py:184-189](backend/app/middleware/error_handler.py#L184-L189)

**Issue:** In DEBUG mode, full tracebacks are exposed to clients. If DEBUG is accidentally enabled in production, sensitive information could leak.

```python
if settings.is_production:
    message = "An unexpected error occurred..."
else:
    details = {
        "error_type": error_type,
        "traceback": traceback.format_exc(),  # Exposes internals
    }
```

**Recommendation:**
- Add explicit check: `if settings.DEBUG and not settings.is_production`
- Never send tracebacks to clients, even in DEBUG mode (log instead)

---

### 2.3 SQL Injection via Search Queries (Severity: HIGH)

**File:** [jobs.py:158-166](backend/app/api/v1/endpoints/jobs.py#L158-L166)

**Issue:** Search term is used directly with `ilike` without parameterization concerns.

```python
if q:
    search_term = f"%{q}%"  # User input directly in query
    query = query.filter(
        or_(
            Job.title.ilike(search_term),
            Job.company.ilike(search_term),
            Job.description.ilike(search_term)
        )
    )
```

**Assessment:** SQLAlchemy's `ilike` uses parameterized queries, so this is SAFE. However, the `%` wildcards could enable expensive full-table scans.

**Recommendation:**
- Add input length validation (max 100 chars)
- Consider full-text search index for better performance

---

### 2.4 Unbounded Job Scraping (Severity: HIGH)

**File:** [jobs.py:386-446](backend/app/api/v1/endpoints/jobs.py#L386-L446)

**Issue:** Users can trigger job scraping tasks without limits. No validation on `max_results_per_source`.

```python
class ScrapeJobsRequest(BaseModel):
    sources: List[str]
    keywords: Optional[List[str]] = None
    max_results_per_source: int = 50  # No maximum validation!
```

**Risk:** Users could request excessive scraping, overwhelming external APIs and increasing costs.

**Recommendation:**
```python
max_results_per_source: int = Field(default=50, le=100, ge=1)
```

---

## 3. MEDIUM SEVERITY ISSUES

### 3.1 CORS Allows All Methods (Severity: MEDIUM)

**File:** [main.py:85-86](backend/app/main.py#L85-L86)

```python
allow_methods=["*"],
allow_headers=["*"],
```

**Recommendation:** Restrict to used methods: `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]`

---

### 3.2 Missing CSRF Protection (Severity: MEDIUM)

**Issue:** No CSRF tokens for state-changing operations. Relies entirely on JWT authentication.

**Recommendation:**
- Add `SameSite=Strict` cookie attribute
- Consider CSRF tokens for sensitive operations (profile update, CV upload)

---

### 3.3 Password Hashing Uses Default Rounds (Severity: MEDIUM)

**File:** [security.py:15](backend/app/core/security.py#L15)

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**Recommendation:** Explicitly set work factor: `rounds=12` minimum for production.

---

### 3.4 No Pagination Limits Enforced (Severity: MEDIUM)

**File:** [jobs.py:145](backend/app/api/v1/endpoints/jobs.py#L145)

```python
page_size: int = Query(20, ge=1, le=100, description="Items per page")
```

**Assessment:** Good - pagination is limited to 100 items. No issues found.

---

### 3.5 File Upload Size Validation After Read (Severity: MEDIUM)

**File:** [cvs.py:140-151](backend/app/api/v1/endpoints/cvs.py#L140-L151)

**Issue:** File content is read into memory BEFORE size validation.

```python
file_content = await file.read()  # Entire file loaded
file_size = len(file_content)
if file_size > max_size:  # Checked AFTER loading
```

**Recommendation:** Check `Content-Length` header first, use streaming for large files.

---

## 4. SCALABILITY ASSESSMENT

### 4.1 Candidate Volume Capacity

**Current Architecture:**
- PostgreSQL via Supabase (with Connection Pooler fallback)
- Redis for Celery task queue
- Background job scraping via Celery workers

**Assessed Limits:**

| Component | Current Limit | Scalability Concern |
|-----------|--------------|---------------------|
| Job Matching | 200 jobs/request | AI embeddings called per job - O(n) API calls |
| Recommendations | 50/user | Pre-computed, scales well |
| Usage Tracking | In-memory | Won't scale beyond single instance |
| Job Scraping | No limits | Could overwhelm external APIs |
| CV Storage | 10MB limit | Reasonable |

### 4.2 AI API Cost Projections

**Per-User Costs (estimated):**
- CV Parsing: ~$0.02-0.05
- Job Matching (200 jobs): ~$0.10-0.20 per batch
- Cover Letter: ~$0.03-0.05
- Recommendations: ~$0.20 per generation

**For 10,000 users (monthly):**
- Conservative: ~$500-1,000/month
- Heavy usage: ~$2,000-5,000/month

### 4.3 Database Scalability

**Strengths:**
- Connection pooler fallback for IPv6 issues
- Proper indexes on frequently queried columns
- UUID primary keys

**Concerns:**
- No read replicas configured
- No database-level rate limiting
- Job table could grow large without archival strategy

**Recommendation:**
- Implement job archival after 30 days
- Add read replica for job searches
- Consider partitioning jobs table by `scraped_at`

---

## 5. AI COMPONENT AUDIT

### 5.1 Provider Integration Status

| Provider | Status | Concern |
|----------|--------|---------|
| OpenAI | Implemented | Primary provider, fallback not tested |
| Gemini | Implemented | Import error handling in place |
| Groq | Implemented | Listed as cost-optimized option |
| Grok | Implemented | Least tested provider |

### 5.2 AI Safety Measures

**Implemented:**
- Prompt injection detection patterns (sanitizer.py)
- Sensitive data detection (SSN, credit cards, API keys)
- HTML stripping from inputs

**Missing:**
- Output validation (AI responses not sanitized)
- Hallucination detection
- Content moderation for generated cover letters

### 5.3 Cost Control Measures

**Implemented:**
- Token usage tracking
- Provider-level cost calculation
- Cost optimization routing option

**Missing:**
- Per-user spending caps
- Automatic provider switching on quota exhaustion
- Cost alerts/notifications

---

## 6. AUTHENTICATION & AUTHORIZATION AUDIT

### 6.1 Authentication Flow

**Implementation:** Supabase Auth with JWT tokens

**Strengths:**
- JWT verification via Supabase REST API
- HTTPBearer scheme
- 5-second timeout on auth verification

**Concerns:**
- No refresh token handling in backend
- No session invalidation endpoint (logout is client-side only)

### 6.2 Authorization

**Resource Access Control:**

| Resource | Authorization Check | Status |
|----------|---------------------|--------|
| CVs | `user_id == current_user.id` | PASS |
| Applications | `user_id == current_user.id` | PASS |
| Jobs (delete) | `added_by_user_id == current_user.id` | PASS |
| Profiles | `user_id == current_user.id` | PASS |
| Scraping jobs | `user_id == current_user.id` | PASS |

**Finding:** All user resources properly scoped. No IDOR vulnerabilities found.

---

## 7. ERROR HANDLING & LOGGING AUDIT

### 7.1 Error Handling

**Strengths:**
- Global error handler middleware
- Request ID tracking for tracing
- Structured JSON error responses
- Database-specific error handling

**Weaknesses:**
- Some endpoints catch generic `Exception` and log but re-raise
- AI provider errors not always gracefully handled

### 7.2 Logging

**Implementation:** structlog with JSON in production, console in dev

**Strengths:**
- Request context binding
- Log level filtering
- Third-party logger suppression (urllib3, httpx)

**Concerns:**
- No log aggregation configured
- No alerting integration

---

## 8. SECURITY CHECKLIST (OWASP Top 10)

| Category | Status | Notes |
|----------|--------|-------|
| A01 Broken Access Control | PASS | Proper user scoping |
| A02 Cryptographic Failures | PASS | bcrypt, JWT HS256 |
| A03 Injection | WARN | Sanitizer exists but not universally applied |
| A04 Insecure Design | WARN | Rate limiting design flaw |
| A05 Security Misconfiguration | WARN | DEBUG mode could leak info |
| A06 Vulnerable Components | CHECK | Run `pip-audit` before release |
| A07 Auth Failures | PASS | Supabase handles auth properly |
| A08 Data Integrity | WARN | AI outputs not validated |
| A09 Logging Failures | PASS | Good logging coverage |
| A10 SSRF | N/A | No user-controlled URLs fetched |

---

## 9. RECOMMENDATIONS SUMMARY

### Must Fix Before Release (CRITICAL)

1. Implement per-user rate limiting with Redis
2. Persist usage tracking to database
3. Apply sanitizer to ALL AI inputs consistently
4. Add graceful degradation for missing AI keys
5. Add request body size limits

### Should Fix Soon (HIGH)

6. Validate job scraping limits
7. Remove tracebacks from error responses completely
8. Add search input length validation
9. Run `pip-audit` and update vulnerable dependencies

### Recommended Improvements (MEDIUM)

10. Restrict CORS methods
11. Add output validation for AI responses
12. Implement per-user AI spending caps
13. Add job archival strategy
14. Configure log aggregation (e.g., Datadog, Sentry)

---

## 10. PRODUCTION READINESS CHECKLIST

- [ ] Fix CRITICAL issues (Section 1)
- [ ] Fix HIGH severity issues (Section 2)
- [ ] Run `pip-audit` for dependency vulnerabilities
- [ ] Configure production environment variables
- [ ] Set `DEBUG=False` and verify error messages
- [ ] Test rate limiting with load testing
- [ ] Configure Sentry DSN for error tracking
- [ ] Set up database backups
- [ ] Configure CloudFlare or similar CDN
- [ ] Document API rate limits for users
- [ ] Create runbook for AI provider failures
- [ ] Set up monitoring dashboards

---

## Appendix A: Files Audited

### Backend Core
- [main.py](backend/app/main.py) - Application entry point
- [config.py](backend/app/core/config.py) - Configuration management
- [security.py](backend/app/core/security.py) - JWT and password handling
- [database.py](backend/app/core/database.py) - Database connection

### API Endpoints
- [auth.py](backend/app/api/v1/endpoints/auth.py) - Authentication
- [jobs.py](backend/app/api/v1/endpoints/jobs.py) - Job management
- [cvs.py](backend/app/api/v1/endpoints/cvs.py) - CV management
- [applications.py](backend/app/api/v1/endpoints/applications.py) - Applications
- [profiles.py](backend/app/api/v1/endpoints/profiles.py) - User profiles
- [ai.py](backend/app/api/v1/endpoints/ai.py) - AI usage stats

### AI Components
- [base.py](backend/app/ai/base.py) - AI provider interface
- [router.py](backend/app/ai/router.py) - Provider routing
- [usage_tracker.py](backend/app/ai/usage_tracker.py) - Usage tracking
- [ai_service.py](backend/app/services/ai_service.py) - AI service layer
- [ai_job_matcher.py](backend/app/services/ai_job_matcher.py) - Job matching
- [recommendation_generator.py](backend/app/services/recommendation_generator.py) - Recommendations

### Security & Middleware
- [sanitizer.py](backend/app/utils/sanitizer.py) - Input sanitization
- [error_handler.py](backend/app/middleware/error_handler.py) - Error handling
- [logging.py](backend/app/core/logging.py) - Logging configuration
- [dependencies.py](backend/app/api/v1/dependencies.py) - Auth dependencies

### Models
- [job.py](backend/app/models/job.py) - Job model
- Other models verified via exploration

---

**Report Generated:** 2026-01-30
**Auditor:** Claude Code Auditor
**Next Review:** After CRITICAL fixes implemented
