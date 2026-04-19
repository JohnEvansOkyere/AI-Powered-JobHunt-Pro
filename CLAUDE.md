# CLAUDE.md

Operating guide for Claude (and other coding agents) working on `AI-Powered-JobHunt-Pro`. This complements `AGENTS.md` — when both exist, treat `AGENTS.md` as the authoritative short rules and this file as the extended map of the codebase.

Higher-priority instructions from the user, system, or developer messages always override this file.

## 1. What the product does

AI-Powered Job Hunt Pro is a SaaS platform for candidates that:

- Authenticates users via Supabase Auth and stores rich career profiles.
- Lets users upload/manage CVs and parses them into structured JSON.
- Scrapes job postings from ~12 public sources and a generic AI/URL parser.
- Precomputes AI-based recommendations using OpenAI embeddings with title boosting.
- Generates tailored CVs and cover letters per job application.
- Tracks saved jobs and application lifecycle.

Read `README.md`, `docs/PROJECT_PLAN.md`, and the most recent audit (`docs/PRODUCTION_SYSTEM_AUDIT_2026-04-18.md`) before making non-trivial architectural changes.

## 2. Repository layout

```
AI-Powered-JobHunt-Pro/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint, lifespan starts APScheduler
│   │   ├── core/                   # config, database, logging, security, supabase_client
│   │   ├── api/v1/
│   │   │   ├── router.py           # mounts: auth, users, profiles, cvs, ai, jobs,
│   │   │   │                       # applications, external_jobs
│   │   │   ├── dependencies.py     # get_current_user (Supabase /user call per request)
│   │   │   └── endpoints/          # auth, users, profiles, cvs, ai, jobs,
│   │   │                            # applications, external_jobs
│   │   ├── models/                 # SQLAlchemy: user, user_profile, cv, job,
│   │   │                            # job_match, job_recommendation, application,
│   │   │                            # scraping_job
│   │   ├── services/               # ai_service, ai_job_matcher, cv_parser,
│   │   │                            # cv_generator, cover_letter_generator,
│   │   │                            # external_job_parser, job_matching_service(+_optimized),
│   │   │                            # job_processor, job_scraper_service,
│   │   │                            # recommendation_generator
│   │   ├── ai/                     # router.py, usage_tracker.py, providers/
│   │   ├── scrapers/               # 12 scrapers + base.py (adzuna, remotive, remoteok,
│   │   │                            # jooble, findwork, indeed, linkedin, joinrise,
│   │   │                            # arbeitnow, hiringcafe, serpapi, ai_scraper)
│   │   ├── scheduler/              # APScheduler jobs (in-process)
│   │   ├── tasks/                  # Celery app + ai_processing, job_scraping,
│   │   │                            # periodic_tasks
│   │   ├── middleware/             # error_handler, request_logger, request_size_limit
│   │   ├── utils/                  # sanitizer, job_scraper helpers
│   │   └── exceptions/             # typed exceptions
│   ├── tests/                      # pytest suite (conftest, test_auth, test_cvs,
│   │                                # test_jobs, test_profiles, test_ai_router,
│   │                                # test_sanitizer)
│   ├── scripts/                    # ops scripts
│   ├── requirements.txt            # dev deps (pinned fastapi, loose for AI libs)
│   ├── requirements-prod.txt
│   ├── pytest.ini / pyproject.toml
│   └── start_celery_worker.sh / start_celery_beat.sh
├── frontend/
│   ├── app/                        # Next.js App Router: auth/, dashboard/
│   │   └── dashboard/              # jobs, applications, cv, profile, external-jobs, settings
│   ├── components/                 # auth/, jobs/ (JobCard, JobFilters), layout/,
│   │                                # modals/, profile/
│   ├── lib/
│   │   ├── api/                    # typed clients: client.ts, jobs, cvs,
│   │   │                            # applications, profiles, external-jobs, savedJobs
│   │   ├── auth.ts, profile-utils.ts, skills.ts
│   │   ├── supabase/ (SSR + browser clients)
│   │   └── utils/
│   ├── hooks/, styles/, types/
│   ├── next.config.js, tailwind.config.ts, tsconfig.json
│   └── package.json                # Next 14, React 18, Zod, Zustand, RHF, Framer Motion
├── docs/                           # setup, phases, feature docs, audits
├── migrations/                     # 003/004/005 incremental SQL (drifts from full setup)
├── docs/SUPABASE_SETUP_COMPLETE.sql# canonical-ish full schema (still drifts)
├── docker-compose.yml
└── README.md
```

## 3. Environments and commands

- Python: 3.11+. Backend venv lives at `backend/venv`. Always use `backend/venv/bin/python` and `backend/venv/bin/pip`.
- Node: 18+.

Default commands (from `AGENTS.md` — keep identical):

- Frontend type check: `cd frontend && npm run type-check`
- Frontend build: `cd frontend && npm run build`
- Frontend dev: `cd frontend && npm run dev`
- Backend dev server: `cd backend && venv/bin/uvicorn app.main:app --reload`
- Backend tests: `cd backend && venv/bin/python -m pytest -q`
- Targeted tests: `cd backend && venv/bin/python -m pytest tests/<file>.py -q`
- Coverage (already configured): `cd backend && venv/bin/python -m pytest --cov=app`
- Celery worker: `cd backend && ./start_celery_worker.sh`
- Celery beat: `cd backend && ./start_celery_beat.sh`

Search: prefer `rg` and `rg --files`. Avoid `find`/`grep` per workspace rules.

## 4. Core backend concepts

### Configuration
`backend/app/core/config.py` loads a single `Settings` instance from `.env`. Keys to be aware of:
- `ENVIRONMENT`, `DEBUG` (defaults to `True` — see audit P1.4).
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_STORAGE_BUCKET` (default `cvs`).
- `DATABASE_URL` (validated to start with `postgresql://` or `postgresql+psycopg2://`).
- AI keys: `OPENAI_API_KEY`, `GROK_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`.
- Scraper keys: `SERPAPI_API_KEY`, `JOOBLE_API_KEY`, `FINDWORK_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`.
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.
- `CORS_ORIGINS`, `ALLOWED_HOSTS` (default `["*"]` — audit P1.4).
- `CRON_SECRET` (optional — audit P0.3 flags this as a blocker).
- `AI_RATE_LIMIT_PER_MINUTE`, `SCRAPING_RATE_LIMIT_PER_MINUTE` (declared but not currently enforced).

Never print or commit `.env` values. Inspecting variable names is fine.

### Authentication
- `backend/app/api/v1/dependencies.py::get_current_user` validates the bearer token by calling Supabase Auth `/user` on every request (audit P1.6 flags this for latency/coupling).
- Protected endpoints depend on `current_user["id"]`. Most user-owned reads/writes must filter by that id.
- The frontend wraps pages in `ProtectedRoute`, but the backend is the real authorization boundary.

### Database and Supabase
- SQLAlchemy engine in `backend/app/core/database.py` uses `DATABASE_URL` directly — Supabase RLS does not protect server-side queries. Always add `WHERE user_id = :current_user` in application code.
- Storage: Supabase bucket `cvs` for original CVs; tailored CVs currently stored under `tailored-cvs/{user_id}/...` (path mismatch with SQL storage policies in `docs/SUPABASE_SETUP_COMPLETE.sql` — audit P0.2).
- Migrations: `migrations/003_add_saved_jobs_feature.sql`, `004_create_job_recommendations.sql`, `005_add_external_jobs_support.sql`. They drift from the full setup SQL and the models (audit P2.12). Reconcile both when touching schema.

### Models
`backend/app/models/` defines: `User`, `UserProfile`, `CV`, `Job`, `JobMatch`, `JobRecommendation`, `Application`, `ScrapingJob`. Status enums in code (e.g., application `saved`, `submitted`, `interviewing`, `rejected`, `offer`) do not match older SQL constraints — verify before persisting.

### AI and scraping
- `app/ai/router.py` selects between OpenAI/Grok/Gemini/Groq and tracks usage via `usage_tracker.py`.
- `app/services/external_job_parser.py` fetches arbitrary URLs and passes them to Jina Reader as a fallback — audit P0.1 marks this as an SSRF blocker. Any change here must add a scheme allowlist (`https` only), IP/host validation (block private/loopback/link-local/multicast/metadata), redirect validation, size/content-type/timeout limits, and per-user quotas.
- `app/services/cv_parser.py` inserts raw CV text into prompts; `app/utils/sanitizer.py` has partial injection defenses (audit P1.10).
- Scheduler: `app/scheduler/job_scheduler.py` runs in-process via FastAPI lifespan. Under multiple workers each will run it (audit P1.11). Prefer Celery Beat or a distributed lock when changing scheduled work.

### Middleware
- `CORSMiddleware`, `RequestSizeLimitMiddleware` (content-length only, chunked bodies bypass — audit P2.13), `ErrorHandlerMiddleware`, `RequestLoggingMiddleware`, and `TrustedHostMiddleware` (only in non-debug).

## 5. Core frontend concepts

- Next.js App Router under `frontend/app/`. Dashboard is the main authenticated surface.
- Supabase clients: `frontend/lib/supabase/` (SSR vs browser). Auth helpers in `frontend/lib/auth.ts`.
- All API calls go through `frontend/lib/api/*` — keep types in sync with backend response models. If you change a backend Pydantic model, update the matching `*.ts` file.
- Validation: `zod` + `react-hook-form` via `@hookform/resolvers`.
- State: `zustand` stores per feature.
- Do not introduce `dangerouslySetInnerHTML` for any scraped, AI-derived, or user-submitted content. The one existing instance in `frontend/app/dashboard/applications/generate/[jobId]/page.tsx` is an open audit item (P1.5) and should be removed, not copied.
- Run `npm run type-check` after any TypeScript-facing change.

## 6. Security and data-handling rules (must-read)

Treat the following as sensitive: user CVs (original and tailored), parsed CV JSON, cover letters, profile data, auth tokens, Supabase keys, AI prompts, and generated application text.

Hard requirements when editing relevant code:

1. **Ownership filtering**: every read/write on user data must filter by `current_user["id"]`. Add negative authorization tests when adding endpoints.
2. **Storage URLs**: do not return `get_public_url` for candidate CVs or tailored CVs. Use short-lived signed URLs after an ownership check.
3. **External fetching**: any path that fetches a user-supplied URL must enforce scheme allowlist, DNS/IP filtering (before and after redirects), response size limits, and timeouts.
4. **Cron endpoints**: require `X-Cron-Secret` in production. If `ENVIRONMENT=production` and `CRON_SECRET` is empty, startup must fail — do not silently allow open cron.
5. **Rate limits and quotas**: AI generation, scraping triggers, and recommendation generation must be rate-limited per user (Redis-backed) and budget-capped.
6. **Untrusted content rendering**: never render scraped/AI text as HTML without a vetted sanitizer; prefer plain text.
7. **Prompt construction**: isolate untrusted text with clear delimiters, keep system/developer instructions privileged, and validate LLM output with a schema before persistence.
8. **Retention and deletion**: when deleting a user, application, or CV, also delete all derived files (tailored CVs, cached parses) and cached recommendations.

## 7. Engineering rules

- Read the relevant file(s) before editing. Do not speculate.
- Keep changes scoped to the user's request. Do not refactor unrelated files, rename symbols for style, or revert user changes unless explicitly asked.
- Prefer small, reviewable diffs. Do not add speculative abstractions.
- Use `apply_patch` for manual edits.
- Match existing style and imports. Do not add docstrings/comments that narrate the code.
- If tests exist for the area you touch, run them. If no test exists and the change has behavioral impact, add one.
- After substantive edits, run the relevant type check or tests before handing off.

## 8. Testing and CI expectations

- Backend tests live in `backend/tests/`. Known-flaky areas: `test_ai_router.py` fails when real env AI keys leak into tests (audit P2.15). Inject settings or clear AI env vars for hermetic runs.
- `test_cvs.py.bak`, `test_jobs.py.bak`, `test_profiles.py.bak` are intentionally disabled snapshots — do not re-enable without updating them to the current models/endpoints.
- Coverage configuration exists via `pyproject.toml` / `pytest.ini`. Do not commit `htmlcov/` or `coverage.xml`.
- Frontend has no test runner yet; `npm run type-check` and `npm run build` are the gate.
- There is no CI workflow in-repo yet. Manual runs of the default commands stand in for CI.

## 9. Documentation expectations

- When behavior changes, update the closest doc in `docs/`. Common ones: `SETUP.md`, `JOB_SCHEDULER_SETUP.md`, `JOB_SCRAPING_GUIDE.md`, `AI_CV_GENERATOR_*`, `ERRORS_AND_SOLUTIONS.md`, `DEPLOYMENT.md`.
- When schema changes:
  - Add a new `migrations/NNN_*.sql` with a sequential number.
  - Update `docs/SUPABASE_SETUP_COMPLETE.sql` so a fresh project boots cleanly.
  - Note any irreversible change in the PR description.
- Audit docs (pattern `docs/PRODUCTION_SYSTEM_AUDIT_*.md`) should separate confirmed findings, inferred risks, and verification gaps, and cite file and line numbers.

## 10. Production readiness status (as of 2026-04-18)

The most recent audit marks the system as **not production-ready** for real candidates. Open P0 blockers:

1. SSRF via external job URL parsing (`backend/app/services/external_job_parser.py`).
2. Public (non-expiring) URLs for tailored CVs (`backend/app/services/cv_generator.py`, `backend/app/api/v1/endpoints/applications.py`).
3. Optional cron auth and missing rate limits on AI/scraping/recommendation endpoints (`backend/app/api/v1/endpoints/jobs.py`).

Major P1/P2 items: permissive production defaults, `dangerouslySetInnerHTML`, per-request Supabase auth calls, backend bypassing RLS, global AI usage stats, partial retention model, partial prompt-injection defenses, in-process scheduler duplication, schema/migration drift, incomplete request-size protection, broad `ILIKE` search, flaky AI router tests.

Before claiming production readiness: close all P0s plus the first five P1s, make the full backend test suite run deterministically, and verify a fresh-database migration run against both `docs/SUPABASE_SETUP_COMPLETE.sql` and the `migrations/` files.

## 11. Handy pointers

- Entrypoints: `backend/app/main.py`, `frontend/app/page.tsx`.
- Auth dependency: `backend/app/api/v1/dependencies.py`.
- AI router: `backend/app/ai/router.py`.
- Scheduler: `backend/app/scheduler/job_scheduler.py`.
- External job parsing: `backend/app/services/external_job_parser.py`.
- Tailored CV generation: `backend/app/services/cv_generator.py`.
- Cover letter generation: `backend/app/services/cover_letter_generator.py`.
- Recommendations: `backend/app/services/recommendation_generator.py` + `app/services/ai_job_matcher.py`.
- Frontend API client base: `frontend/lib/api/client.ts`.
