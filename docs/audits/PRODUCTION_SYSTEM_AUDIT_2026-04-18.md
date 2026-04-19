# Production System Audit - AI-Powered JobHunt Pro

Audit date: 2026-04-18  
Scope: FastAPI backend, Next.js frontend, Supabase schema/storage docs, migrations, job scraping, AI generation, CV handling, and local verification commands.

## Executive Assessment

This system has a credible product foundation: authenticated candidate accounts, profile and CV management, job scraping, recommendations, saved jobs, and AI-generated application material. The core ownership checks for profile, CV, and application CRUD are generally present.

It is not ready for high-trust production handling of candidate CVs and job-search data until the P0/P1 items below are fixed. The main blockers are SSRF exposure, public/non-expiring CV URLs, optional cron authentication, missing rate limits and quotas around AI/scraping, permissive production defaults, XSS risk from job descriptions, migration drift, and incomplete test reliability.

## Verification Performed

- `frontend`: `npm run type-check` passed.
- `backend`: targeted `venv/bin/python -m pytest tests/test_ai_router.py -q` completed with `2 failed, 17 passed, 1 skipped`.
- `backend`: full `venv/bin/python -m pytest -q` collected 93 tests and reached `tests/test_auth.py`, but did not complete and was manually stopped. Treat backend CI health as failing/unknown until the full suite runs deterministically.

## P0 Findings

### 1. SSRF Through External Job URL Parsing

`ExternalJobURLRequest` validates only that the input is a URL, then the backend fetches it with redirects enabled. There is no scheme allowlist, DNS/IP validation, private network blocklist, redirect target validation, response size limit, or content-type guard.

Evidence:
- `backend/app/services/external_job_parser.py:55` accepts arbitrary URLs for parsing.
- `backend/app/services/external_job_parser.py:140` performs `httpx.AsyncClient(..., follow_redirects=True).get(url)`.
- `backend/app/services/external_job_parser.py:103` also forwards the URL to Jina Reader as a fallback.

Impact: an authenticated user can make the production backend fetch internal services, cloud metadata endpoints, admin panels, localhost services, or large responses.

Required fix:
- Allow only `https`.
- Resolve hostname and block private, loopback, link-local, multicast, reserved, and metadata IP ranges before and after redirects.
- Disable redirects or validate every redirect hop.
- Enforce response byte limits, content-type limits, timeout budgets, and per-user quotas.
- Log only domain and request ID, not full sensitive URLs.

### 2. Generated CVs Use Public URLs Instead of Expiring Signed URLs

Tailored CVs contain candidate PII. The generator uploads them under `tailored-cvs/{user_id}/...` and returns `get_public_url`. The application download endpoint also returns a public URL. This is either broken for private buckets or unsafe for public buckets; in neither case is it a robust production privacy model.

Evidence:
- `backend/app/services/cv_generator.py:125` stores tailored CVs under `tailored-cvs/{user_id}`.
- `backend/app/services/cv_generator.py:147` returns `get_public_url`.
- `backend/app/api/v1/endpoints/applications.py:591` returns a download URL using `get_public_url`.
- Storage policies in `docs/SUPABASE_SETUP_COMPLETE.sql:499` assume paths start with `{user_id}`, which does not match `tailored-cvs/{user_id}`.

Impact: candidate CVs can become non-expiring links if the bucket is public, or downloads can fail if the bucket is private and RLS is correctly enforced.

Required fix:
- Keep the bucket private.
- Store generated files under `{user_id}/tailored-cvs/...` or add explicit storage policies for the generated path.
- Return short-lived signed URLs only after checking application ownership.
- Delete generated artifacts when applications/users are deleted.

### 3. Costly Cron and AI Paths Are Not Safely Authenticated or Rate Limited

Production cron auth is optional. If `CRON_SECRET` is empty, unauthenticated callers can trigger cleanup and all-user recommendation generation. Authenticated users can also trigger scraping and per-user recommendations without implemented rate limiting or quotas.

Evidence:
- `backend/app/core/config.py:96` defines `CRON_SECRET` as optional.
- `backend/app/api/v1/endpoints/jobs.py:483` and `backend/app/api/v1/endpoints/jobs.py:519` allow cron endpoints when no secret is configured.
- `backend/app/api/v1/endpoints/jobs.py:414` lets any authenticated user start scraping.
- `backend/app/api/v1/endpoints/jobs.py:548` lets any authenticated user generate recommendations.
- Rate limit settings exist at `backend/app/core/config.py:111`, but no middleware/enforcement was found.

Impact: database churn, third-party scraping abuse, AI provider cost spikes, and denial of service.

Required fix:
- In production, fail startup unless `CRON_SECRET` is set for cron endpoints or remove public cron endpoints entirely.
- Add Redis-backed rate limits by user/IP/endpoint.
- Add per-user AI budgets, job scrape quotas, and queue concurrency limits.
- Make all-user recommendation generation admin/cron-only.

## P1 Findings

### 4. Production Defaults Are Too Permissive

The app defaults to `DEBUG=True` and `ALLOWED_HOSTS=["*"]`. API docs are enabled when debug is true. SQLAlchemy echoes queries when debug is true.

Evidence:
- `backend/app/core/config.py:25` and `backend/app/core/config.py:26`.
- `backend/app/core/config.py:89`.
- `backend/app/main.py:75`.
- `backend/app/core/database.py:87`.

Required fix: create production settings validation that fails startup if `ENVIRONMENT=production` and `DEBUG=True`, wildcard hosts/origins are present, `CRON_SECRET` is empty, or required observability/security settings are missing.

### 5. XSS Risk From Job Descriptions

The frontend injects job descriptions as HTML with `dangerouslySetInnerHTML`. Jobs are scraped, user-submitted, and AI-derived, so this content is untrusted.

Evidence:
- `frontend/app/dashboard/applications/generate/[jobId]/page.tsx:277`.

Required fix: render plain text or sanitize HTML with a vetted sanitizer and a strict allowlist. Prefer plain text for job descriptions.

### 6. Auth Verification Depends on a Supabase Network Call Per Request

Every protected API request calls Supabase Auth `/user`. That increases latency, couples availability to Supabase on every request, and makes outages look like user auth failures.

Evidence:
- `backend/app/api/v1/dependencies.py:47`.

Required fix: validate JWTs locally against Supabase JWKS with cache and expiry/audience checks. Use Supabase `/user` only when live revalidation is required.

### 7. Backend Bypasses RLS, So App Authorization Must Be Treated as Primary

The backend uses direct SQLAlchemy database access. Supabase RLS policies protect client-side Supabase access, but server-side queries can bypass them depending on the database role in `DATABASE_URL`.

Evidence:
- SQLAlchemy engine in `backend/app/core/database.py:84`.
- RLS policies exist in `docs/SUPABASE_SETUP_COMPLETE.sql:302`, but backend queries do not use Supabase user context.

Required fix: centralize ownership-scoped query helpers, add negative authorization tests for every user-owned object, and use the least-privileged DB role possible.

### 8. AI Usage Stats Are Visible to Any Authenticated User

AI usage and cost endpoints are protected only by normal authentication and appear to return global usage.

Evidence:
- `backend/app/api/v1/endpoints/ai.py:50`.
- `backend/app/api/v1/endpoints/ai.py:78`.

Required fix: restrict to admins or return per-user statistics only.

### 9. CV and AI Data Retention Needs a Privacy Model

The system stores raw CV text, parsed CV JSON, cover letters, generated CV paths, prompts, and generation settings. There is no clear retention policy, export/delete workflow for all generated artifacts, or encryption strategy beyond provider defaults.

Evidence:
- `backend/app/models/cv.py` stores `raw_text` and `parsed_content`.
- `backend/app/models/application.py` stores generated materials and `generation_prompt`.
- CV deletion removes the original CV file, but generated tailored CV cleanup is not complete.

Required fix: define retention windows, delete all derived files/data on user deletion, avoid storing full prompts unless required, encrypt sensitive columns if supported, and document data processor exposure to AI providers.

### 10. Prompt Injection Defenses Are Partial

External job text gets regex sanitization, but CV parsing inserts raw CV text directly into prompts. Regex-based injection removal is not enough for LLM security.

Evidence:
- Raw CV prompt inclusion at `backend/app/services/cv_parser.py:170`.
- External job sanitizer exists, but model output still controls persisted structured fields.

Required fix: isolate untrusted text with clear delimiters, do not let source content override system/developer instructions, validate output schemas strictly, and test prompt-injection payloads for CVs and job postings.

### 11. Multi-Process Scheduler Can Duplicate Work

The FastAPI lifespan starts APScheduler in-process. In production with multiple workers or replicas, each process can start a scheduler and duplicate scraping, cleanup, and recommendation jobs.

Evidence:
- Scheduler starts in `backend/app/main.py:42`.

Required fix: move scheduled jobs to a single worker/managed cron or add a distributed lock.

## P2 Findings

### 12. Schema and Migration Drift Is High

The complete setup SQL and incremental migrations do not fully match the current models and product behavior.

Examples:
- Base applications status allows only `draft`, `reviewed`, `finalized`, `sent`, while code uses `saved`, `submitted`, `interviewing`, `rejected`, `offer`.
- `migrations/005_add_external_jobs_support.sql:30` constrains `jobs.source` to a list missing sources used by code such as `remotive`, `joinrise`, and `adzuna`.
- `migrations/004_create_job_recommendations.sql:20` creates a partial index using `NOW()`, which is not valid for immutable index predicates in PostgreSQL.
- `job_recommendations.user_id` has no FK in `migrations/004_create_job_recommendations.sql:8`.

Required fix: generate a canonical schema from the current models, reconcile migrations, and test migrations against a fresh database in CI.

### 13. Request Size Protection Is Incomplete

The request size middleware only checks `Content-Length`; chunked requests without it pass through.

Evidence:
- `backend/app/middleware/request_size_limit.py` explicitly allows requests without `Content-Length`.

Required fix: enforce streaming body limits at the ASGI/proxy layer and app layer.

### 14. Search and Matching Performance Will Degrade

Job search uses broad `ILIKE '%term%'` across title, company, and description. Recommendations can be generated on demand and in the background. This will degrade as job volume grows.

Required fix: use PostgreSQL full-text search or trigram indexes intentionally, cap background work, and precompute recommendations in a controlled queue.

### 15. Test Suite and Dependency Hygiene Need CI Ownership

The AI router tests currently fail because real environment API keys initialize providers despite tests expecting none. The full suite did not finish in this session. There are many Pydantic v2 deprecation warnings.

Required fix:
- Make tests hermetic by clearing AI env vars or injecting settings.
- Add CI jobs for backend tests, frontend type-check/build, migration smoke tests, and security scans.
- Run `pip-audit` and `npm audit` in CI with a documented triage workflow.

## Strengths

- User-owned profile, CV, application, and saved-job reads generally filter by current user.
- CV upload has extension checks, empty-file checks, and a 10 MB explicit limit.
- API response models are mostly typed.
- RLS policies and storage policies exist as a starting point.
- Frontend TypeScript currently type-checks.
- The product has a coherent domain model for candidate profiles, CVs, jobs, applications, and recommendations.

## Recommended Remediation Order

1. Block SSRF and remove public CV URLs.
2. Enforce production config validation, cron auth, and rate limits.
3. Remove `dangerouslySetInnerHTML` for job descriptions.
4. Make auth verification local and cached.
5. Reconcile schema/migrations and add migration CI.
6. Fix backend tests and require full CI before deployment.
7. Add privacy retention/deletion workflows for original and generated CV data.
8. Move scheduled jobs out of API processes or add distributed locking.

## Production Readiness Gate

Do not treat this as production-ready for real candidates until all P0 items and the first five P1 items are closed, backend tests run deterministically, and a fresh-database migration test passes.
