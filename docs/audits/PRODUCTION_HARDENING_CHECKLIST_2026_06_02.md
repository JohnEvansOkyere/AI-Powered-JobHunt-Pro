# Production Hardening Checklist

Date: 2026-06-02
Source: Cross-check of `PRODUCTION_READINESS_REPORT_2026_06_01.md`

## P0 Launch Blockers

- [x] Add SSRF protection to external job URL parsing:
  - [x] Require HTTPS by default.
  - [x] Resolve DNS before fetch and reject loopback, private, link-local, multicast, reserved, and metadata IPs.
  - [x] Manually follow redirects and revalidate every hop.
  - [x] Stream responses with a hard byte cap.
  - [x] Add unit tests for blocked URL classes.
- [x] Lock cron endpoints:
  - [x] Require `CRON_SECRET` for `/api/v1/jobs/cleanup-old`.
  - [x] Require `CRON_SECRET` for `/api/v1/jobs/recommendations/generate-all`.
  - [x] Require `CRON_SECRET` for `/api/v1/recommendations/generate-all`.
  - [x] Fail startup in production when `CRON_SECRET` is empty.
- [x] Add API security headers:
  - [x] `Content-Security-Policy`
  - [x] `Strict-Transport-Security` in production
  - [x] `X-Frame-Options`
  - [x] `X-Content-Type-Options`
  - [x] `Referrer-Policy`
  - [x] `Permissions-Policy`

## P1 Production Controls

- [x] Make production config fail closed:
  - [x] Reject `DEBUG=True` when `ENVIRONMENT=production`.
  - [x] Reject wildcard `ALLOWED_HOSTS` in production.
  - [x] Reject localhost-only/default `CORS_ORIGINS` in production.
- [x] Initialize Sentry when `SENTRY_DSN` is configured.
- [x] Improve `/health` so it verifies database and Redis availability.
- [x] Fix request-size limiting for chunked request bodies.
- [x] Add HTTP-layer rate limiting for scraping, external URL parsing, AI routes, and cron routes.
- [x] Add CI workflow for backend tests, frontend type-check, and frontend build.

## P2 / Follow-up

- [x] Add frontend error boundaries.
- [x] Add public jobs route metadata. No individual public job detail route exists in the current frontend.
- [x] Update `next.config.js` image allowlist for production company logos.
- [x] Clean migration numbering gap and remove `migrations/test.py`.
- [x] Add privacy policy, terms, user export, and user deletion workflow.

## Current Remaining Work

- Resolve the existing full backend test-suite failures before release. The 2026-06-02 full run failed with 20 failures and 21 errors across older auth/CV/jobs/profiles/sanitizer tests, including missing test fixtures.
- Run deployment smoke tests after the backend suite is clean.
- Verify the Supabase Auth admin deletion path in staging with the production service-role key configured.
- Review legal copy with counsel before public launch.

## Architecture Decisions

- Account deletion removes user-owned candidate data, CV records, stored CV files, applications, recommendations, embeddings, scraping jobs, and notification records.
- User-added external job catalog rows are preserved and detached by clearing `jobs.added_by_user_id` instead of being deleted. This prevents one user's account deletion from cascading into other users' recommendations or application records.
- Supabase Auth deletion is best-effort after local candidate data deletion. Staging must verify the service-role key has `auth.admin.delete_user` permissions before public launch.

## Confirmed Non-Runtime Finding

- Public/non-expiring tailored CV URLs are not present in the current runtime code. CV tailoring was removed in `migrations/007_remove_cv_tailoring.sql`, `applications` no longer exposes tailored CV fields, and the only active CV download path uses owner checks plus Supabase signed URLs.

## Verification Notes

- `cd backend && venv/bin/python -m py_compile app/api/v1/endpoints/users.py` passed.
- `cd backend && venv/bin/python -m pytest tests/test_production_hardening.py -q` passed earlier on 2026-06-02: 7 tests.
- `cd backend && venv/bin/python -m pytest tests/test_user_privacy.py tests/test_production_hardening.py -q` passed: 10 tests.
- `cd frontend && npm run type-check` passed.
- `cd frontend && npm run build` passed.
- `cd backend && venv/bin/python -m pytest -q` failed: 20 failed, 154 passed, 1 skipped, 21 errors. Failures are outside the new account export/deletion code and include existing missing fixtures such as `create_test_cv`, `create_test_job`, and `db_session`.
