# Database migrations

Incremental SQL migrations for the Supabase/Postgres database. Apply them in
order against the production database (and any staging/dev copy).

> Numbering skips 006 — there is no migration 006. Jumping from 005 to 007 is
> intentional.

## Current migrations

| Migration | Status | What it does |
|---|---|---|
| `003_add_saved_jobs_feature.sql` | Should already be applied | Saved-jobs schema (pre-pivot) |
| `004_create_job_recommendations.sql` | Should already be applied | Original `job_recommendations` table |
| `005_add_external_jobs_support.sql` | Should already be applied | Columns/indexes for the external-jobs flow (the flow itself is retired, the columns stay) |
| `007_remove_cv_tailoring.sql` | **Apply** | Drops `tailored_cv_path`, `cover_letter`, `application_email`, `ai_model_used`, `generation_prompt`, `generation_settings`, `user_edits` from `applications`; tightens the `status` enum to `saved / applied / dismissed / hidden / interviewing / rejected / offer` and backfills legacy values |
| `008_recommendations_v2.sql` | **Apply** | Enables `pgvector`, creates `job_embeddings` and `user_embeddings` (model-tagged), extends `job_recommendations` with `tier` + sub-score columns + `user_id` FK, adds supporting indexes |
| `009_add_whatsapp.sql` | **Apply** | Creates `notification_preferences` (WhatsApp opt-in + digest time + timezone + opt-out), `whatsapp_messages` (append-only send audit with unique-by-idempotency-key index), `whatsapp_incoming_events` (webhook audit for status + user replies), plus a trigger that keeps `notification_preferences.updated_at` fresh |

All migrations are wrapped in `BEGIN/COMMIT` and use `IF [NOT] EXISTS`, so
re-running them is safe.

## Recommended order

If you're bringing a fresh environment up to date:

```bash
# 1. Apply migrations in order
psql "$DATABASE_URL" -f migrations/007_remove_cv_tailoring.sql
psql "$DATABASE_URL" -f migrations/008_recommendations_v2.sql
psql "$DATABASE_URL" -f migrations/009_add_whatsapp.sql

Configure Meta to call your API **callback URL**
`https://<your-api-host>/api/v1/webhooks/whatsapp` (GET for verify, POST for
events). Set `WHATSAPP_VERIFY_TOKEN` to match the verify token you enter in
Meta, and `WHATSAPP_APP_SECRET` for `X-Hub-Signature-256` verification.

# 2. Clean up orphaned tailored-CV files from Supabase Storage
cd backend
venv/bin/python scripts/maintenance/delete_tailored_cvs.py

# 3. Backfill the embedding cache so Tier 1 / Tier 2 have something to show
venv/bin/python scripts/maintenance/backfill_embeddings.py
```

If you administer the database via the Supabase SQL editor, paste the files
in the same order.

## After 008

Migration 008 sizes all vector columns for **768 dimensions** (Gemini
`gemini-embedding-001`). If you flip `AI_EMBEDDING_PROVIDER` from Gemini to
OpenAI later, you must re-embed — see §3.1 of
`docs/RECOMMENDATIONS_V2_PLAN.md`. Rows stamped with a different `model` stay
in place but are ignored at read time because queries filter by `model`.

If your Postgres does not have the `pgvector` extension available, use the
`float8[]` fallback block at the bottom of `008_recommendations_v2.sql` in
place of the main DDL.

## Adding a new migration

1. Name it `NNN_short_description.sql` using the next unused number.
2. Wrap everything in `BEGIN; ... COMMIT;`.
3. Prefer `IF NOT EXISTS` / `IF EXISTS` so re-runs are no-ops.
4. Document rollback steps inline as a comment.
5. Update this README's table.
6. If the schema of a SQLAlchemy model changes, touch the model file in the
   same PR — the backend doesn't run migrations automatically.

## `test.py`

`migrations/test.py` is a local scratch file, not a migration. Ignore it; it
is intentionally untracked.
