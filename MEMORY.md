# MEMORY.md — VeloxaHire Candidate Platform + Ecosystem Context

> **For AI agents:** Read this file before starting any task. Update the Change Log at the bottom every time you complete a task — date, what changed, and why. This file is the living memory of the system across all sessions.

---

## 1. The Ecosystem — Two Products, One Platform

This is **not** a standalone app. It is one half of a two-product employment ecosystem:

| Product | Repo | Purpose | Users |
|---|---|---|---|
| **VeloxaRecruit** (ATS) | `AI-JOb-Assistant/` | Recruiter-facing: job creation, CV screening, AI interviews, hiring pipeline | Recruiters / HR managers |
| **VeloxaHire** (this repo) | `AI-Powered-JobHunt-Pro/` | Candidate-facing: job discovery, AI recommendations, applications, CV generation | Job seekers |

The products cooperate but are **not collapsed**. Each has its own database, auth, and deployment.

---

## 2. VeloxaHire — What It Does

- Authenticates candidates via Supabase Auth
- Stores rich career profiles and CVs (parsed into structured JSON)
- Scrapes jobs from ~12 public sources (Adzuna, Remotive, RemoteOK, Jooble, etc.)
- Mirrors recruiter-posted jobs from VeloxaRecruit ATS via a scheduled sync
- Runs AI recommendation engine (OpenAI embeddings + title boosting) every 12 hours
- Generates tailored CVs and cover letters per application
- Tracks saved jobs and application lifecycle

---

## 3. Tech Stack — VeloxaHire

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11+), SQLAlchemy, Uvicorn |
| Database | Supabase (PostgreSQL) — RLS **not** relied on server-side; enforce in app code |
| Cache / Queue | Redis, Celery (worker + beat), APScheduler (in-process, legacy) |
| Frontend | Next.js App Router (React 18, TypeScript), Tailwind CSS, Framer Motion |
| Auth | Supabase Auth — bearer token validated per request via `/auth/v1/user` call |
| AI | OpenAI (embeddings + GPT-4o), Grok, Gemini, Groq as fallbacks |
| Storage | Supabase bucket `cvs` for original CVs; `tailored-cvs/{user_id}/...` for generated |
| Hosting | Backend: Render. Frontend: Vercel |
| Design tokens | `brand-turquoise-*` (primary), `neutral-*` (text/bg), amber (tier1 match) |

---

## 4. Tech Stack — VeloxaRecruit (ATS)

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.12), Gunicorn + Uvicorn, DigitalOcean Droplet |
| Database | Supabase (PostgreSQL + Auth + Storage + RLS) — latest migration: **065** |
| Cache | Redis (same server) |
| Frontend | Next.js 16 (React 18, TypeScript), Vercel |
| AI | OpenAI GPT-4o/mini (interviews + analysis), Groq Llama-3.3-70B (CV screening) |
| TTS/STT | ElevenLabs (TTS), Deepgram / OpenAI Whisper (STT) |
| Payments | Paystack (Ghana focus — GHS + USD) |
| Email | Resend + Jinja2 |
| Auth | Supabase Auth + app-issued JWT (HS256, cookie-based) |

---

## 5. The Integration — How the Two Products Connect

### Source-of-truth rules (never violate these)
- **ATS owns** recruiter-created jobs and applications to those jobs
- **VeloxaHire owns** scraped jobs, candidate profiles, recommendations, and a mirrored copy of published ATS jobs
- The candidate-side mirror is **never** canonical — it is a projection for search/display only
- The candidate platform **never** writes directly into ATS tables

### Sync flow
```
1. Recruiter creates/updates job in ATS
2. ATS stores canonical job
3. VeloxaHire Celery Beat polls every 10 minutes:
   GET https://api.veloxarecruit.com/integrations/published-jobs?updated_since=<timestamp>
   Header: X-Candidate-Sync-Token: <shared secret>
4. VeloxaHire upserts mirrored job (source='recruiter', origin_system='ats')
5. Job appears on candidate Job Board (Local Jobs tab)
6. Candidate clicks Apply → lands on ATS public apply page
7. ATS stores canonical application
```

### Sync endpoint (ATS side)
- Route: `GET /integrations/published-jobs` (VeloxaRecruit backend)
- Auth: `X-Candidate-Sync-Token` header — env var `CANDIDATE_SYNC_TOKEN` on ATS, `ATS_SYNC_TOKEN` on VeloxaHire
- Returns: published/hidden job projections (candidate-safe fields only)
- File: `backend/app/api/published_jobs.py` in VeloxaRecruit repo

### Sync service (VeloxaHire side)
- File: `backend/app/services/ats_job_sync_service.py`
- Scheduled: `backend/app/tasks/periodic_tasks.py` → `scheduler.sync_ats_jobs` every 10 minutes
- Enabled by: `ATS_SYNC_ENABLED=true` + `ATS_PUBLISHED_JOBS_URL` + `ATS_SYNC_TOKEN` in `.env`
- Mirrored fields: `origin_system='ats'`, `origin_job_id`, `origin_updated_at`, `ats_organization_id`, `organization_name`, `organization_logo_url`, `publication_status`
- DB constraint: unique on `(origin_system, origin_job_id)`

---

## 6. Frontend Navigation Structure (current)

```
Sidebar:
  Dashboard         → /dashboard
  Job Match         → /dashboard/recommendations    (AI-ranked tiers: Highly recommended, Likely a fit)
  All Jobs          → /dashboard/jobs               (browse all jobs, two toggles below)
    └─ Overall Jobs → /dashboard/jobs               (all scraped + recruiter jobs)
    └─ Local Jobs   → /dashboard/jobs?view=board    (ATS recruiter jobs only, source='recruiter')
  Applications      → /dashboard/applications
  Profile           → /dashboard/profile
  Settings          → /dashboard/settings

Public:
  Browse Jobs       → /jobs                          (anonymous browse/search/filter)
  Job Detail        → /jobs/[id]                     (anonymous SEO-indexed detail + public apply link)
```

### Key page decisions
- **Job Match** shows only tier1 (Highly recommended) and tier2 (Likely a fit) — tier3 "All roles" was removed 2026-05-20
- **Public Jobs** lives at `/jobs` and `/jobs/[id]` — anonymous users can browse, view details, and open public apply links
- **All Jobs** under `/dashboard/jobs` remains the authenticated dashboard browse surface
- **Apply for anonymous users** opens the public recruiter/source apply link; signup prompts sell recommendations/tracking after intent
- **Recommendations** (Job Match) remain behind auth — AI matching requires a profile

---

## 7. Anonymous / Public Access

As of 2026-06-20:
- `/jobs` is the public browse-first job board. Anonymous visitors can search, filter, and view jobs.
- `/jobs/[id]` is the public job detail route with per-job metadata and `JobPosting` JSON-LD.
- Backend `GET /api/v1/jobs/` uses **optional auth** (`get_optional_user`) — no token = jobs still returned.
- Backend `GET /api/v1/jobs/{job_id}` is public for non-archived jobs, so public detail pages work without login.
- Public Apply links remain open. Candidates can leave to the recruiter/source application page without creating an account.
- Signup is the upgrade path for recommendations, saved jobs, match scoring, CV/profile setup, alerts, and application tracking.
- `/dashboard/jobs` remains the authenticated dashboard job browser.

---

## 8. Key Files — VeloxaHire

| Purpose | File |
|---|---|
| FastAPI entrypoint | `backend/app/main.py` |
| Auth dependency (required) | `backend/app/api/v1/dependencies.py::get_current_user` |
| Auth dependency (optional) | `backend/app/api/v1/dependencies.py::get_optional_user` |
| Jobs search endpoint | `backend/app/api/v1/endpoints/jobs.py::search_jobs` |
| ATS sync service | `backend/app/services/ats_job_sync_service.py` |
| Celery periodic tasks | `backend/app/tasks/periodic_tasks.py` |
| Recommendation generator | `backend/app/services/recommendation_generator.py` |
| Sidebar nav | `frontend/components/layout/DashboardLayout.tsx` |
| Public jobs list | `frontend/app/jobs/page.tsx`, `frontend/app/jobs/JobsClient.tsx` |
| Public job detail | `frontend/app/jobs/[id]/page.tsx` |
| Job Match page | `frontend/app/dashboard/recommendations/page.tsx` |
| All Jobs page | `frontend/app/dashboard/jobs/page.tsx` |
| Job card | `frontend/components/jobs/JobCard.tsx` |
| Post-apply signup modal | `frontend/components/jobs/PostApplyModal.tsx` |
| DB migrations | `migrations/` (latest: `010_add_ats_job_mirroring.sql`) |

---

## 9. Candidate UX Principles (product decisions, do not reverse without Evans)

- Browse jobs freely without account
- Public job pages should show real inventory before asking for signup
- Apply without account (external link)
- After applying, invite to register — **don't block apply with a gate**
- Profile completion is required for AI recommendations, not for browsing or applying
- Recruiter jobs (source='recruiter') show "Recruiter" emerald badge on cards
- Recommendations mix scraped + recruiter jobs (if they match the profile)

---

## 10. Known Open Items

| Item | Status |
|---|---|
| Post-apply profile CTA for logged-in users | Not built — only anonymous modal exists |
| Sync observability dashboard (last sync, jobs imported/updated/archived) | Backend ops endpoint implemented 2026-06-20; visual admin dashboard not built |
| Manual ATS job backfill command | Backend ops endpoint implemented 2026-06-20: `POST /api/v1/ops/ats-sync/backfill` |
| Webhook events from ATS (job.published, job.updated, job.closed) | Deferred |
| Shared SSO / identity across both products | Deferred |
| SSRF guard in external_job_parser.py | Implemented 2026-06-02 — HTTPS-only default, DNS/IP blocking, redirect revalidation, response byte cap, regression tests |
| Public tailored CV URLs (should be signed) | Verified non-runtime 2026-06-02 — CV tailoring service/columns removed; active CV downloads use signed URLs |
| Production hardening docs follow-up | Remaining: full pre-release gate, staging verification of Supabase Auth admin deletion, counsel review of legal copy |
| Recruiter job posting from inside VeloxaHire (native) | Deferred (plan exists in docs/RECRUITER_JOB_POSTINGS_PLAN.md) |
| "Add job by URL" → tailored CV/cover letter (`source='external'`) | **Retired 2026-07-13** — Evans confirmed it is not coming back. Endpoints unmounted + deleted, orphan rows purged. `external_job_parser.py` service is now dead code (kept only because `test_production_hardening.py` exercises its SSRF guards) — safe to delete with those tests if desired |
| Job retention: "nothing older than 7 days" is not literally true | By design. `cleanup_old_jobs` skips (a) `source='recruiter'` (ATS-owned lifecycle) and (b) any job with an application (protects user history). 3 aged scraped rows currently persist in browse for reason (b) — Evans chose 2026-07-13 to keep this behaviour rather than hide them from browse |
| CLAUDE.md §10 "production readiness" P0 list is stale | Lists SSRF + public tailored-CV URLs as open blockers; both were closed 2026-06-02 (see rows above). Misleads fresh agent sessions — needs a rewrite against current code |

---

## 11. VeloxaRecruit — Known Issues Log

| Date | Issue | Resolution |
|---|---|---|
| 2026-05-20 | `SUPABASE_URL` env var truncated (missing `.co`) — DNS failures on all Supabase calls, users blocked by login rate limiter | Fix: correct URL in DigitalOcean env. Clear Redis key `failed_login:154.161.36.34` |

---

## 12. Change Log

**Agents: append a row every time you complete a task. Never delete rows.**

| Date (UTC) | What changed | Why |
|---|---|---|
| 2026-05-17 | Added ATS sync endpoint `GET /published-jobs` to VeloxaRecruit. Files: `backend/app/api/published_jobs.py`, `backend/app/services/published_job_service.py`, `backend/app/models/published_job.py` | Enable candidate platform to mirror recruiter jobs |
| 2026-05-17 | Updated ecosystem integration docs and checklist | Document decisions and sync architecture |
| 2026-05-20 | VeloxaRecruit: fixed truncated `SUPABASE_URL` env var (`.supabase.` → `.supabase.co`) | DNS resolution failing, all logins returning 401 |
| 2026-05-20 | VeloxaHire sidebar: renamed "Jobs" → "Job Match", added "All Jobs" nav item. File: `DashboardLayout.tsx` | Separate AI recommendation view from browse-all view |
| 2026-05-20 | VeloxaHire: removed tier3 ("All roles") column from Job Match page. File: `recommendations/page.tsx` | Moving all-jobs browsing to dedicated All Jobs page |
| 2026-05-20 | VeloxaHire All Jobs page: renamed toggles to "Overall Jobs" / "Local Jobs". File: `jobs/page.tsx` | Clearer language: Local Jobs = recruiter ATS jobs |
| 2026-05-20 | VeloxaHire: removed ProtectedRoute from All Jobs page; backend search_jobs now uses optional auth via `get_optional_user`. Files: `jobs/page.tsx`, `dependencies.py`, `endpoints/jobs.py` | Allow anonymous users to browse and apply without an account |
| 2026-05-20 | VeloxaHire: created `PostApplyModal` component. Triggers for non-authenticated users after clicking Apply. File: `components/jobs/PostApplyModal.tsx` | Capture anonymous users post-apply with a signup CTA showing 4 value props |
| 2026-05-20 | Audited VeloxaHire recommendation delivery configuration. No application behavior changed; inspected Celery schedule, recommendation generation, WhatsApp config/endpoints, docs, and tests. | Determine whether recommended jobs are generated and sent to users, and identify remaining work |
| 2026-05-20 | Built WhatsApp Tier-1 recommendation delivery: added digest dispatcher/sender service and Celery tasks, hourly Beat schedule, idempotent `whatsapp_messages` audit writes, digest config/env docs, tests, and Settings-page opt-in controls. Files: `backend/app/services/whatsapp_digest.py`, `backend/app/tasks/whatsapp_digest.py`, `backend/app/tasks/celery_app.py`, `backend/app/core/config.py`, `backend/.env.example`, `backend/tests/test_periodic_tasks.py`, `backend/tests/test_whatsapp_digest.py`, `frontend/lib/api/whatsapp.ts`, `frontend/app/dashboard/settings/page.tsx`, `docs/deployment/CELERY.md`, `docs/RECOMMENDATIONS_V2_PLAN.md` | Complete the missing path that sends recommended jobs to users after recommendations are generated |
| 2026-06-02 | Cross-checked `docs/audits/PRODUCTION_READINESS_REPORT_2026_06_01.md` against current backend/frontend code and appended this memory row. No application behavior changed. | Verify whether Claude's production-readiness findings are still present or already resolved |
| 2026-06-02 | Added production hardening checklist and implemented first blocker fixes. Files: `docs/audits/PRODUCTION_HARDENING_CHECKLIST_2026_06_02.md`, `backend/app/services/external_job_parser.py`, `backend/app/api/v1/endpoints/jobs.py`, `backend/app/api/v1/endpoints/recommendations.py`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/middleware/security_headers.py`, `backend/app/middleware/request_size_limit.py`, `backend/app/middleware/__init__.py`, `backend/requirements.txt`, `backend/requirements-prod.txt`, `backend/tests/test_production_hardening.py`, `MEMORY.md`. Behavior changed from open SSRF/optional cron auth/no API security headers/static health/chunked body bypass to guarded URL fetches, fail-closed cron auth, production config guardrails, security headers, Sentry init, DB+Redis health checks, and hardening regression tests. | Start resolving the production-readiness audit for a public candidate platform with high security expectations |
| 2026-06-02 | Reconciled production hardening docs after the interrupted session. Files: `docs/audits/PRODUCTION_HARDENING_CHECKLIST_2026_06_02.md`, `docs/audits/PRODUCTION_READINESS_REPORT_2026_06_01.md`, `MEMORY.md`. Marked implemented rate limiting, CI, frontend error boundaries, and image allowlist; added a 2026-06-02 report update and remaining-work list. | Recover the prior checklist/report state after the laptop freeze and make the remaining launch work explicit |
| 2026-06-02 | Completed remaining production-hardening follow-ups. Files: `backend/app/api/v1/endpoints/users.py`, `frontend/lib/api/users.ts`, `frontend/app/dashboard/settings/page.tsx`, `frontend/app/privacy/page.tsx`, `frontend/app/terms/page.tsx`, `frontend/app/dashboard/jobs/layout.tsx`, `migrations/006_reserved_noop.sql`, `migrations/README.md`, `migrations/test.py`, `docs/audits/PRODUCTION_HARDENING_CHECKLIST_2026_06_02.md`, `docs/audits/PRODUCTION_READINESS_REPORT_2026_06_01.md`, `MEMORY.md`. Added account data export/deletion, legal pages, public jobs metadata status, migration no-op placeholder, and removed the scratch migration file; verified tailored-CV public URLs are not present in runtime code. | Finish the launch-readiness checklist items that remained after the interrupted audit session |
| 2026-06-02 | Ran production-hardening verification and documented results. `users.py` compiled, focused hardening tests passed, frontend type-check passed, and frontend build passed. Full backend suite failed with 20 failures and 21 errors across existing auth/CV/jobs/profiles/sanitizer tests, including missing fixtures. Files updated: `docs/audits/PRODUCTION_HARDENING_CHECKLIST_2026_06_02.md`, `docs/audits/PRODUCTION_READINESS_REPORT_2026_06_01.md`, `MEMORY.md`. | Make the launch gate status explicit after implementing the remaining checklist items |
| 2026-06-02 | Strengthened account-deletion architecture and tests. Files: `backend/app/api/v1/endpoints/users.py`, `backend/tests/test_user_privacy.py`, `docs/audits/PRODUCTION_HARDENING_CHECKLIST_2026_06_02.md`, `docs/audits/PRODUCTION_READINESS_REPORT_2026_06_01.md`, `MEMORY.md`. Deletion now detaches user-added external jobs by clearing `added_by_user_id` instead of deleting shared job rows; added focused privacy tests and re-ran privacy + hardening tests successfully. | Avoid compromising shared job catalog integrity while satisfying user data deletion requirements |
| 2026-06-01 | UI/UX production polish across all dashboard pages using ui-ux-pro-max skill. Files: `frontend/app/globals.css` (added card/shadow/gradient utility system), `frontend/components/layout/DashboardLayout.tsx` (sidebar accent bar, gradient avatar ring, glassmorphism header, logout hover), `frontend/app/dashboard/page.tsx` (stat cards with gradient accents & icon containers, CTA accent strip, action card hover lift), `frontend/components/jobs/JobCard.tsx` (hover elevation, cursor-pointer, premium buttons), `frontend/app/dashboard/recommendations/page.tsx` (card-interactive, improved buttons/bookmarks/empty states), `frontend/app/dashboard/applications/page.tsx` (card elevation, improved empty states/buttons), `frontend/app/dashboard/settings/page.tsx` (replaced "Coming soon" with proper placeholder UI, improved form inputs with brand focus rings, section dividers), `docs/audits/UI_UX_AUDIT_2026-06-01.md` (full audit report). Type-check and build passed clean (15/15 pages). | Make dashboard feel premium and production-grade before public launch while preserving existing brand colors and landing page design |
| 2026-06-06 | Follow-up UI polish pass on remaining pages. Files: `frontend/app/dashboard/profile/page.tsx` (all section cards use `.card` utility, gradient progress bar, rounded-xl inputs/selects/textareas with brand focus rings, cursor-pointer on buttons), `frontend/app/profile/setup/page.tsx` (fixed legacy `border-primary-700` spinner to brand-turquoise, improved heading typography, cursor-pointer), `frontend/app/dashboard/jobs/page.tsx` (empty state uses `.card`, rounded-xl pagination buttons, bold heading). Type-check and build passed clean (17/17 pages). | Complete full design system consistency across every dashboard page |
| 2026-06-20 | Implemented browse-first public job discovery. Files: `frontend/app/jobs/page.tsx`, `frontend/app/jobs/JobsClient.tsx`, `frontend/app/jobs/[id]/page.tsx`, `frontend/app/page.tsx`, `backend/app/api/v1/endpoints/jobs.py`, `MEMORY.md`. Anonymous visitors can now open `/jobs`, search/filter jobs, view `/jobs/{id}` detail pages with SEO metadata + `JobPosting` JSON-LD, and open public apply links. Signup is positioned as the upgrade for AI recommendations, saving, tracking, CV/profile setup, and alerts. Backend `GET /api/v1/jobs/{job_id}` is public for non-archived jobs. Also corrected memory from stale `/published-jobs` to canonical `/integrations/published-jobs`. | Make VeloxaHire browse-first so candidates see inventory before signup; keep recommendations as the signup carrot |
| 2026-06-20 | VeloxaRecruit post-apply capture CTA implemented in companion repo. ATS `frontend/app/apply/[jobId]/page.tsx` now links successful applicants to `${NEXT_PUBLIC_VELOXAHIRE_URL}/jobs` after the ATS application is already submitted; no PII is passed and no VeloxaHire account is auto-created. ATS `frontend/.env.example` documents `NEXT_PUBLIC_VELOXAHIRE_URL`; production Vercel must set it for the CTA to render. | Close Phase 1 of the ecosystem loop: use the high-intent post-apply moment to send candidates into VeloxaHire's browse-first job board |
| 2026-06-20 | Added ATS sync observability and manual backfill backend. Files: `backend/app/services/ats_sync_status_service.py`, `backend/app/services/ats_job_sync_service.py`, `backend/app/tasks/periodic_tasks.py`, `backend/app/api/v1/endpoints/ops.py`, `backend/app/api/v1/router.py`, `backend/app/core/config.py`, `backend/.env.example`, `backend/tests/test_ats_sync_status_service.py`, `backend/tests/test_ats_job_sync_service.py`. Scheduled syncs now record `running` / `success` / `failed` status, timestamps, trigger, errors, and counts to Redis key `ats-sync:status` with local fallback. Operators can call `GET /api/v1/ops/ats-sync/status` for stale status and `POST /api/v1/ops/ats-sync/backfill` for a full sync; both require `X-Cron-Secret`. `ATS_SYNC_STALE_AFTER_MINUTES` defaults to 20. This is admin/operator visibility, not recruiter-facing. | Prevent the ATS job mirror from silently failing and give Evans a recovery trigger without exposing integration internals to recruiters |
| 2026-06-20 | Implemented signed ATS apply-to-VeloxaHire signup handoff. [ATS] now mints a 15-minute `handoff_token` after successful public application submission and its CTA opens `/register?h=<opaque token>` on VeloxaHire when available. [HIRE] added `HANDOFF_TOKEN_SECRET` / `PREVIOUS_HANDOFF_TOKEN_SECRET`, `POST /api/v1/auth/handoff/verify`, `/register` redirect, and signup prefill from verified token claims (`purpose=ats_apply`, `iss=veloxarecruit`, `aud=veloxahire`, applicant email/name/phone/job/application ids). Invalid/expired tokens fall back to blank signup. No raw PII in the URL, no CV handoff, no auto-signup. `frontend` type-check/build passed; focused handoff verifier tests passed. **Production requires the same `HANDOFF_TOKEN_SECRET` on both backends.** | Convert high-intent applicants into VeloxaHire candidates with less typing while preserving consent and keeping the recruiter application flow ungated |
| 2026-06-20 | Added `docs/deployment/DIGITALOCEAN_MIGRATION.md` — runbook for moving the VeloxaHire backend off Render free tier (no background workers, so Celery beat never runs → periodic jobs including the 10-min ATS sync don't fire) to a DigitalOcean droplet running three separate systemd processes: web (`gunicorn app.main:app -k uvicorn.workers.UvicornWorker`), Celery worker (`celery -A app.tasks.celery_app worker`), and Celery beat (`celery -A app.tasks.celery_app beat`, single instance only), plus local Redis broker/backend, Nginx + Certbot. Documents the 8 scheduled tasks, env (incl `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` + matching `ATS_SYNC_TOKEN`/`HANDOFF_TOKEN_SECRET`), 2GB+ sizing, verify steps (`celery inspect ping`, ats-sync status shows `last_trigger=scheduled`), and gotchas (one beat only, add gunicorn to requirements, retire the manual backfill cron after cutover). Docs only — no code/infra changed. | Founder is on Render free tier (jobs can't self-run) and plans to migrate to DO; needs a doc to run all jobs as separate processes from the main web server |
| 2026-06-21 | Created a **shared cross-repo contract doc**, byte-identical in both repos: `docs/ECOSYSTEM_CONTRACT.md` (this repo) and `AI-JOb-Assistant/docs/ECOSYSTEM_CONTRACT.md`. Single source of truth for the VeloxaRecruit↔VeloxaHire integration handshake so any Claude/Codex session in either repo gets the same picture. Captures: roles/ownership (ATS canonical for jobs+applications, VeloxaHire mirrors a projection via `source='recruiter'`, never writes ATS); current state (Phases 0–2 done, conversational-interview WIP on the ATS branch, SSO/Phase 3 deferred); and the contract surfaces — job sync (consume `GET /integrations/published-jobs` via `ats_job_sync_service.py`, `ATS_SYNC_TOKEN` must equal ATS `CANDIDATE_SYNC_TOKEN`, 10-min Celery beat `scheduler.sync_ats_jobs`, ops `GET/POST /api/v1/ops/ats-sync/{status,backfill}`, no pagination cursor yet), handoff token (HS256 `HANDOFF_TOKEN_SECRET` must match ATS, iss=veloxarecruit/aud=veloxahire/purpose=ats_apply/15-min, `POST /api/v1/auth/handoff/verify` rate-limited + single-use via `_consume_handoff_jti`/`handoff:jti`), apply loop, shared secrets, migration coupling (010/011), release gate, and a Drift Watch noting the 2026-06-21 ATS-side audit is stale on handoff single-use/rate-limit (HIRE code already implements both). Docs only — no code touched. **Rule going forward:** edit both copies in the same session and bump the contract version + synced change log. | Evans asked for one agreed contract doc, identical in both repos, fully updated with the unification work, so new sessions understand the whole integration without re-deriving it |
| 2026-06-21 | Closed danger-audit code item #10: **restricted the Next.js image optimizer host**. `frontend/next.config.js` `images.remotePatterns` changed from wildcard `**.supabase.co` to the single project host `jeixjsshohfyxgosfzuj.supabase.co`, so the optimizer can no longer be driven to fetch/resize images from arbitrary Supabase projects (image-proxy / droplet cost+OOM abuse vector). Own logos/avatars unaffected (same host). Also untracked build artifacts (`backend/coverage.xml`, `frontend/tsconfig.tsbuildinfo`, `.ipynb_checkpoints/`) + added `.gitignore` rules (audit #12). The companion narrowing of the ATS public apply response (audit #6/#8) landed in `AI-JOb-Assistant`. Updated `docs/ECOSYSTEM_CONTRACT.md` (both repo copies, v2026-06-21.5). | Audit flagged the wildcard image host as an open proxy/cost vector; pinned it to the real project host |
| 2026-06-21 | Fixed cross-site nav double-pathing on the candidate landing. Prod Vercel env `NEXT_PUBLIC_VELOXARECRUIT_URL` was set to `https://www.veloxarecruit.com/register` (with a path) and `app/page.tsx` appended `/get-started` → `/register/get-started`. `frontend/app/page.tsx` now derives `new URL(env).origin` via a `siteOrigin()` helper then appends `/register` (Evans confirmed `/register` is the correct ATS signup destination, not `/get-started`). Path-safe even if env carries a path, but env should be a bare origin. Companion ATS fix: `LandingPageClient.tsx` + `apply/[jobId]/page.tsx` (`/jobs/jobs`). Updated `docs/ECOSYSTEM_CONTRACT.md` §7 origin-only env rule (both copies, v2026-06-21.6). | Recruiter CTA on VeloxaHire pointed at `/register/get-started`; root cause was env var containing a path + hardcoded `/get-started` append |
| 2026-06-21 | Simplified the "I'm hiring" nav link to use the env var verbatim. `frontend/app/page.tsx` — `VELOXARECRUIT_START_URL = process.env.NEXT_PUBLIC_VELOXARECRUIT_URL || 'https://www.veloxarecruit.com/register'` (removed the `siteOrigin()` helper and the appended `/register`). Destination is now whatever the env var is — change it in Vercel + redeploy, no code edit. Added `NEXT_PUBLIC_VELOXARECRUIT_URL=https://www.veloxarecruit.com/register` to `frontend/.env.local` with a doc comment. Contract `docs/ECOSYSTEM_CONTRACT.md` §7 updated (both copies, v2026-06-21.7). | Evans wanted the nav buttons dead simple — just send users to the URL in the env var, no path logic in code |
| 2026-07-10 | Filled in `docs/deployment/DIGITALOCEAN_MIGRATION.md` (Droplet creation, Namecheap DNS for `api.veloxahire.org`, Nginx+Certbot SSL steps, fixed Ubuntu 22.04→24.04 + `python3.11`→system `python3` inconsistency) and closed its two open checklist items: added `gunicorn>=21.2.0` to `backend/requirements.txt`, and created `.github/workflows/deploy-backend.yml` (test-gate + SSH deploy + restart of all three systemd services `veloxahire`/`veloxahire-worker`/`veloxahire-beat` + health check, mirroring VeloxaRecruit's `deploy-backend.yml` pattern; triggers only on push to `main` since PR/push testing is already covered by `ci.yml`, to avoid duplicate CI runs). Confirmed with Evans: VeloxaHire gets its **own separate Droplet** (not shared with VeloxaRecruit's), since VeloxaHire's worker+beat+embeddings workload is heavier/different and could OOM-starve the revenue-critical ATS box if colocated. No droplet created yet, no DNS live yet, no deploy executed — docs/CI scaffolding only, ready for Evans to run once the Droplet exists and GitHub Secrets (`DO_DEPLOY_SSH_KEY`/`DO_DEPLOY_HOST`/`DO_DEPLOY_USER`) are set. | Evans bought the `veloxahire.org` domain and asked to prepare the DO migration + automated CI/CD deploy pipeline, continuing from the earlier discussion about VeloxaHire signup email verification (Resend/Supabase SMTP) |
| 2026-07-11 | **VeloxaHire backend live on DigitalOcean**, Droplet `ubuntu-s-1vcpu-1gb-lon1` (London/LON1, matches Supabase region), walked through interactively with Evans over SSH. Actual sizing deviated from the doc's 2GB recommendation to **1GB RAM + a 2GB swap file** for cost reasons; mitigated with conservative Celery settings (`--concurrency=1 --max-tasks-per-child=100`) — doc's §3/§5 updated to match. All three systemd services (`veloxahire`, `veloxahire-worker`, `veloxahire-beat`) confirmed `active (running)`; Nginx + Certbot SSL live at `https://api.veloxahire.org` (health check returns db+redis healthy). Celery fully verified end-to-end in production: worker responds to `inspect ping`, all 7 scheduled tasks registered, and the 10-minute ATS sync fired on its own schedule (`GET /api/v1/ops/ats-sync/status` returned `last_trigger:"scheduled"`, `status:"success"`, jobs fetched from VeloxaRecruit) — proving the whole point of the migration (jobs that never ran on Render's free tier now run unattended). Fixed along the way: a stray `venv/` created in the wrong directory from an early failed attempt (blocked `git clone`), a missing `.env` file (systemd reported it as a generic "resources" failure, not an obvious missing-file error), and a GitHub Actions deploy failure from unset `DO_DEPLOY_HOST`/`USER`/`SSH_KEY` secrets (needed a *second*, separate deploy keypair — GitHub Actions→Droplet — distinct from the earlier Droplet→GitHub clone key). Remaining before full cutover: verify `CORS_ORIGINS` in `.env` includes the real `veloxahire.org` frontend origins, switch Vercel's `NEXT_PUBLIC_API_URL` to `https://api.veloxahire.org` and redeploy, soak-test a few days, then decommission Render. | Evans is executing the DO migration prepared the day before; capturing the actual deployed state (1GB not 2GB, real gotchas hit) so a future session doesn't assume the doc's untested happy path is what's actually running |
| 2026-07-11 | **VeloxaHire migration to DigitalOcean fully cut over**, per Evans's confirmation: Vercel custom domain (`veloxahire.org` / `www.veloxahire.org`) added, `NEXT_PUBLIC_API_URL` switched to `https://api.veloxahire.org`, redeployed, live site confirmed working end-to-end against the new backend. Backend is no longer on Render for real traffic. Still open (not yet done, flagged for a future session): retire any external cron hitting `/ops/ats-sync/backfill` manually (Beat now owns the 10-min sync), monitor the 1GB Droplet's memory over the first few days of real traffic (`free -h` / `systemctl status veloxahire-worker`) since it's below the doc's recommended 2GB, confirm the GitHub Actions CI/CD pipeline (`deploy-backend.yml`) deploys a real `backend/` change end-to-end now that systemd+Nginx exist, and decommission the Render service once stable. | Closing out the DO migration thread that started 2026-07-10 with the domain purchase and email-verification discussion |
| 2026-07-13 | **Retired the `external` job feature and fixed job cleanup.** Evans spotted a "5mo ago" job (DeVry, Applied AI Prompt Engineer) in the public browse index and asked why cleanup hadn't removed it. Root cause: it was `source='external'` — a leftover from the retired "paste a job URL → tailored CV/cover letter" flow, which persisted the parsed job as a row in the shared `jobs` table (the same table public browse reads). `cleanup_old_jobs` explicitly exempted `('external','recruiter')`, so those rows never expired; and with `posted_date` NULL the card fell back to `scraped_at` (2026-01-30), displaying the *ingest* date as if it were a posting date. Both rows belonged to `evans@gmail.com`. Changes: (1) `backend/app/api/v1/router.py` — unmounted the `external_jobs` router; (2) **deleted** `backend/app/api/v1/endpoints/external_jobs.py` (`POST /jobs/external/from-url` + `/from-text` were still live and reachable despite no frontend caller); (3) `backend/app/tasks/periodic_tasks.py::cleanup_old_jobs` — exemption narrowed from `notin_(("external","recruiter"))` to `!= "recruiter"`, so any stray external row now expires at 7 days; (4) **purged production data** (backed up first): 2 `jobs` + 1 `applications` (a `saved` app pinning the DeVry row) + 2 `job_recommendations` + 2 `job_embeddings`. Index went 118 → 116 jobs (arbeitnow 70, recruiter 42, serpapi 6; external 0). **Deliberately did NOT apply the 7-day rule to `recruiter` jobs** — they mirror the ATS via an incremental sync keyed on `max(origin_updated_at)` (`ats_job_sync_service.py:85`), so deleting a live published role would *not* resync it (its `origin_updated_at` is below the watermark → silently gone from the candidate index forever) and a full re-fetch would recreate rows with **new UUIDs**, stranding `applications.job_id` + apply-handoff links. Recruiter lifecycle is `publication_status` (published/hidden/archived), not age. Also verified in passing: **Beat + worker are healthy on the DO droplet** (arbeitnow newest scrape 2026-07-13 06:00 UTC, only 2 rows >7d) — the migration did not break the schedulers, so cleanup was running correctly all along. Backend suites covering the touched code pass (67); the 11 failed/21 errored tests in `test_profiles`/`test_cvs`/`test_jobs` are **pre-existing** (identical on a stashed clean tree). | Evans reported stale 5-month-old jobs in browse and asked for cleanup so "job shouldn't exceed 7 days in the system"; investigation showed the scraper/cleanup were fine and the real culprit was a retired feature writing private user data into the public job index |
