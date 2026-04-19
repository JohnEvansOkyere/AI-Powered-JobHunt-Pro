# Recommendations V2 Codebase Match Audit

Date: 2026-04-19
Scope: `docs/RECOMMENDATIONS_V2_PLAN.md` compared against the current backend, frontend, migrations, scripts, and tests.

## Executive Summary

The codebase now has a real Recommendations V2 foundation: tiered recommendation endpoints, embedding tables/models, embedding and rerank services, Celery Beat scheduling, a three-tier frontend surface, and WhatsApp opt-in/webhook backend foundations.

During this audit I fixed several mismatches that would have kept production on the old recommendation stack:

- Legacy scheduled/manual recommendation generation now delegates to `RecommendationEngineV2`.
- `/api/v1/jobs?matched=true` no longer calls the old hard-gated matcher.
- Recommendation API background task injection no longer uses shared default `BackgroundTasks()` instances.
- Profile, CV, and scraped job writes now enqueue embedding refresh tasks.
- Celery Beat recommendation generation now runs every 12 hours, matching the V2 pipeline contract.
- OpenAI embedding fallback now requests 768-dimensional vectors so fallback rows fit the `vector(768)` schema.
- Frontend production build now passes by wrapping `/dashboard/jobs` search-param usage in `Suspense`.

## Confirmed Implemented

- `migrations/007_remove_cv_tailoring.sql`, `008_recommendations_v2.sql`, and `009_add_whatsapp.sql` exist.
- `Application` model and applications API are stripped down to tracking statuses.
- CV tailoring source files and frontend `applications/generate` subtree are absent.
- `GET /api/v1/recommendations`, `POST /api/v1/recommendations/regenerate`, and cron `generate-all` endpoints exist.
- `RecommendationEngineV2` implements cached embeddings, pgvector/Python fallback retrieval, LLM rerank, tier assignment, and tiered persistence.
- Celery Beat replaced FastAPI APScheduler startup.
- Frontend has the three-tier recommendations page and jobs drill-down by tier.
- WhatsApp schema, models, Cloud API client, OTP flow, auth endpoints, webhook signature helper, and STOP handling exist.

## Remaining Gaps

1. `docs/SUPABASE_SETUP_COMPLETE.sql` is stale.
   It still includes `tailored_cv_path`, `cover_letter`, old application statuses, old AI preferences, and does not include V2 embedding/WhatsApp schema. A fresh database from that file will not match migrations 007-009.

2. WhatsApp delivery is not complete.
   Backend opt-in/webhook foundation is present, but the profile/settings frontend panel and daily digest dispatcher are not implemented.

3. Legacy matching modules remain in source.
   `ai_job_matcher.py`, `job_matching_service.py`, `job_matching_service_optimized.py`, and `job_match.py` remain. They are no longer used by `/jobs?matched=true`, but they should either be deleted in a cleanup PR or explicitly documented as deprecated.

4. Recommendation engine still needs production hardening.
   Interest affinity currently uses the user vector against the interest centroid instead of scoring each candidate job against that centroid. Candidate selection also does not yet apply excluded-keyword soft penalties.

5. WhatsApp webhook HMAC is conditional on `WHATSAPP_APP_SECRET`.
   In production, missing `WHATSAPP_APP_SECRET` should be a hard configuration error for webhook processing, not a warning-only skip.

6. Historical docs still describe removed CV-generation features.
   Runtime source is clean, but `docs/features/ai-cv/*`, setup docs, and older audit docs still describe tailored CV and cover-letter generation.

## Verification

- Backend py_compile passed for changed backend modules.
- Targeted backend tests passed: `test_recommendations_v2.py`, `test_periodic_tasks.py`, `test_whatsapp_schema.py` — 61 passed.
- `test_whatsapp_phase4b.py` hangs when it reaches `TestClient(app)` based webhook tests. The first four non-TestClient tests pass. This appears to be a broader app/TestClient middleware issue because a direct `TestClient(app).get("/health")` also hangs.
- Frontend `npm run type-check` passed.
- Frontend `npm run build` passed after adding the Suspense boundary.
