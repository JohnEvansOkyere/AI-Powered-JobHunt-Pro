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
   GET https://api.veloxarecruit.com/published-jobs?updated_since=<timestamp>
   Header: X-Candidate-Sync-Token: <shared secret>
4. VeloxaHire upserts mirrored job (source='recruiter', origin_system='ats')
5. Job appears on candidate Job Board (Local Jobs tab)
6. Candidate clicks Apply → lands on ATS public apply page
7. ATS stores canonical application
```

### Sync endpoint (ATS side)
- Route: `GET /published-jobs` (VeloxaRecruit backend)
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
```

### Key page decisions
- **Job Match** shows only tier1 (Highly recommended) and tier2 (Likely a fit) — tier3 "All roles" was removed 2026-05-20
- **All Jobs** is a **public page** (no ProtectedRoute) — anonymous users can browse and apply
- **Apply for anonymous users** triggers `PostApplyModal` (signup CTA) instead of `markJobApplied`
- **Recommendations** (Job Match) remain behind auth — AI matching requires a profile

---

## 7. Anonymous / Public Access

As of 2026-05-20:
- `/dashboard/jobs` is **publicly accessible** — `ProtectedRoute` removed
- Backend `GET /api/v1/jobs/` uses **optional auth** (`get_optional_user`) — no token = jobs still returned
- Anonymous apply flow: click Apply (external link opens) → `PostApplyModal` appears with signup CTA
- Modal value props: AI matching, match scores, notifications, application tracking
- Modal CTA: "Create free account" → `/auth/signup`

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
| Job Match page | `frontend/app/dashboard/recommendations/page.tsx` |
| All Jobs page | `frontend/app/dashboard/jobs/page.tsx` |
| Job card | `frontend/components/jobs/JobCard.tsx` |
| Post-apply signup modal | `frontend/components/jobs/PostApplyModal.tsx` |
| DB migrations | `migrations/` (latest: `010_add_ats_job_mirroring.sql`) |

---

## 9. Candidate UX Principles (product decisions, do not reverse without Evans)

- Browse jobs freely without account
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
| Sync observability dashboard (last sync, jobs imported/updated/archived) | Not built |
| Manual ATS job backfill command | Not built |
| Webhook events from ATS (job.published, job.updated, job.closed) | Deferred |
| Shared SSO / identity across both products | Deferred |
| SSRF guard in external_job_parser.py | Open P0 (see CLAUDE.md §10) |
| Public tailored CV URLs (should be signed) | Open P0 |
| Recruiter job posting from inside VeloxaHire (native) | Deferred (plan exists in docs/RECRUITER_JOB_POSTINGS_PLAN.md) |

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
