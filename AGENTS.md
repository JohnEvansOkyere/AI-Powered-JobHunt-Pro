# AGENTS.md

## Purpose

This file is the repo-local operating guide for coding agents working on `AI-Powered-JobHunt-Pro`. It supplements higher-priority instructions from the user, system, and developer messages.

## Project Shape

- `backend/` is a FastAPI application using SQLAlchemy, Supabase Auth/Storage, APScheduler, Celery, Redis, and multiple AI providers.
- `frontend/` is a Next.js App Router application using React, TypeScript, Tailwind CSS, Supabase Auth, and a FastAPI client in `frontend/lib/api`.
- `docs/` contains setup, migration, feature, troubleshooting, and audit documentation.
- `migrations/` contains incremental SQL changes that may drift from `docs/SUPABASE_SETUP_COMPLETE.sql`; verify both when touching schema behavior.

## Default Commands

- Frontend type check: `cd frontend && npm run type-check`
- Frontend build: `cd frontend && npm run build`
- Backend tests: `cd backend && venv/bin/python -m pytest -q`
- Targeted backend tests: `cd backend && venv/bin/python -m pytest tests/<file>.py -q`
- Backend app entrypoint: `backend/app/main.py`
- Frontend app entrypoint: `frontend/app/page.tsx`

## Engineering Rules

- Read the relevant code before editing. Prefer `rg` and `rg --files` for search.
- Keep changes scoped to the user request. Do not refactor unrelated files.
- Do not revert, overwrite, or clean up user changes unless the user explicitly asks.
- Use `apply_patch` for manual edits.
- Treat candidate CVs, generated applications, profile data, auth tokens, Supabase keys, and AI prompts as sensitive data.
- Do not print or commit `.env` values. It is acceptable to inspect variable names for audit purposes.
- For production-impacting changes, verify auth, ownership checks, storage access, rate limits, failure modes, and migration compatibility.

## Backend Notes

- Auth is enforced through `get_current_user` in `backend/app/api/v1/dependencies.py`.
- Most user-owned reads and writes should filter by `current_user["id"]`.
- SQLAlchemy uses a direct database connection, so Supabase RLS is not a substitute for backend authorization checks.
- CV storage uses Supabase service-role access in backend code. Be strict about signed URLs, path ownership, and deletion of generated artifacts.
- Scraping and external URL parsing are high-risk paths: guard against SSRF, cost abuse, duplicate work, and untrusted HTML/text.
- AI inputs should be treated as hostile. Sanitize and bound CV/job/profile text before sending it to providers, and validate AI output before persistence.

## Frontend Notes

- Protected pages are wrapped with `ProtectedRoute`, but real authorization must still live in the backend.
- Avoid `dangerouslySetInnerHTML`; job descriptions and AI/scraped text are untrusted.
- Keep API types in `frontend/lib/api/*` aligned with backend response models.
- Run `npm run type-check` after TypeScript-facing changes.

## Documentation Expectations

- If behavior changes, update the closest relevant doc in `docs/`.
- If schema changes, update both migrations and the complete Supabase setup script or clearly document the migration order.
- Audit documents should separate confirmed findings, inferred risks, and verification gaps.

