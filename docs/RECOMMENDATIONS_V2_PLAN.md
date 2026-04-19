# Recommendations V2 + WhatsApp Delivery — Implementation Plan

Status: proposed
Owner: TBD
Target scope: refocus the product on job recommendations and delivery. Remove CV tailoring and cover-letter generation. Ship a three-tier recommendation UI and deliver Tier 1 picks to candidates via WhatsApp Business API.

This plan supersedes the recommendation improvements discussed in the production audit and my earlier three-wave suggestion, and runs in parallel with `docs/RECRUITER_JOB_POSTINGS_PLAN.md`.

## 1. Product decisions

1. **Remove CV tailoring.** The tailored-CV and cover-letter features are dropped from the product. CV *upload and parsing* stays (needed for the matcher).
2. **Recommendations become the core product.** The candidate dashboard's main surface is a three-column view:
   - Column 1 — "Highly Recommended" (Tier 1): the short, confident list.
   - Column 2 — "Likely a Fit" (Tier 2): broader semantic matches worth a look.
   - Column 3 — "All Roles" (Tier 3): full catalog filtered to the user's target category.
3. **WhatsApp is a first-class delivery channel.** Tier 1 picks are pushed to opted-in candidates through the Meta WhatsApp Business API.
4. **Tailoring is not "archived", it is deleted.** Clean repo, smaller attack surface.

## 2. Why

- Tailoring and cover-letter generation carry P0/P1 privacy and injection risk (see `docs/PRODUCTION_SYSTEM_AUDIT_2026-04-18.md` findings 2, 5, 10) for low user value. The candidate rarely uses the generated artifact as-is.
- Embedding-based recommendations are already in place. Investing there produces a clearer product: "we find you jobs and tell you about them."
- WhatsApp, especially in mobile-first markets already represented in your scrapers (Ghana via Joinrise, etc.), is dramatically higher-engagement than email for this use case.

## 3. Architecture overview

```
                    ┌────────────────────────────────────────────┐
                    │  Scheduler (Celery Beat)                   │
                    │  - scrape jobs                             │
                    │  - embed new jobs                          │
                    │  - generate recs for active users          │
                    │  - send WhatsApp Tier-1 digests            │
                    └────────────┬───────────────────────────────┘
                                 │
       ┌─────────────────────────┼────────────────────────┐
       │                         │                        │
┌──────▼──────┐        ┌─────────▼────────┐      ┌────────▼────────┐
│ Scrapers +  │        │ Recommendation   │      │ Notification    │
│ Recruiter   │        │ Engine v2        │      │ Dispatcher      │
│ Postings    │        │ - embed          │      │ - WhatsApp      │
│             │        │ - rerank (LLM)   │      │ - (email later) │
│             │        │ - tier           │      │                 │
└──────┬──────┘        └─────────┬────────┘      └────────┬────────┘
       │                         │                        │
       └─────────────────────────▼────────────────────────┘
                        Postgres / Supabase
                 jobs, user_profiles, cvs,
                 job_recommendations (tiered),
                 job_embeddings, user_embeddings,
                 notification_preferences,
                 whatsapp_messages
```

Key shifts from today:

- Job and user embeddings are **cached** in Postgres (pgvector or raw float8[]), not recomputed per match.
- A small LLM **reranker** runs on the top candidates to turn noisy cosine scores into trustable ranks.
- `JobRecommendation` carries a **tier** column so the API doesn't re-classify on every read.
- Scheduling moves from in-process APScheduler to **Celery Beat** to avoid the in-process scheduler bug (`docs/PRODUCTION_SYSTEM_AUDIT_2026-04-18.md` §11).
- AI providers default to **free tiers** (Gemini for embeddings and rerank) with OpenAI kept as a paid fallback. See §3.1.

## 3.1 AI provider strategy (free-tier first)

Goal: run the recommendation stack at effectively $0 by default and treat paid providers as failover only. All AI calls route through `backend/app/ai/router.py`; provider choice is configurable per task so we can swap without touching business logic.

Task-to-provider mapping (primary → fallback):

| Task | Primary (free) | Fallback (paid) | Notes |
|---|---|---|---|
| Embedding (jobs, users, interest centroids) | **Gemini `text-embedding-004`** — 768-dim, 1,500 RPM free | OpenAI `text-embedding-3-small` | One provider per corpus at a time (rows are model-tagged in `job_embeddings.model`); switching providers = re-embed. |
| LLM reranker (top-50 per user) | **Gemini 1.5 Flash** (free tier generous) or **Groq Llama 3.1 70B** | OpenAI `gpt-4o-mini` | Strict JSON schema; malformed output falls back to `semantic_fit` ordering. |
| External job URL parse / text extraction (existing) | **Gemini 1.5 Flash** | OpenAI `gpt-4o-mini` | Already routed; no change required beyond defaults. |

Environment flags (add to `.env.example`):

```
AI_EMBEDDING_PROVIDER=gemini          # gemini | openai
AI_EMBEDDING_MODEL=text-embedding-004 # gemini default
AI_RERANK_PROVIDER=gemini             # gemini | groq | openai
AI_RERANK_MODEL=gemini-1.5-flash
AI_PROVIDER_FALLBACK_ENABLED=true
```

Router behavior:

- Primary provider is called with a hard timeout (embedding: 5s; rerank: 15s).
- On timeout, 429, 5xx, or quota-exceeded error: fall back once to the paid provider if `AI_PROVIDER_FALLBACK_ENABLED=true`.
- Per-task counter logged (`cache_hit`, `primary_success`, `fallback_success`, `both_failed`). After two weeks we can decide whether to retire the paid fallback entirely.

Consequences:

- Embedding dim changes from 1536 → **768**. The migration in §5.1 assumes the primary provider. If you pick OpenAI as primary, widen the column to 1536 there.
- `job_embeddings.model` is the source of truth for "what model produced this vector". Queries MUST join only vectors with matching `model`; a column-level CHECK or a runtime filter enforces that.
- A provider switch is an offline operation: queue `embed_job` for every active job and `embed_user` for every active user, bounded concurrency, then swap the config. `RecommendationGenerator` tolerates a mixed state by filtering on `model` and treating non-matching rows as "missing".

Cost reality check (so this is a deliberate choice, not a panic): at ~300 new jobs/week and ~1k active users, OpenAI `text-embedding-3-small` is ~$3–4/month. The savings here are *reliability and vendor independence*, not cash. Rerank spend scales with active users and is the real cost — that's why Gemini 1.5 Flash is the primary for it.

## 4. CV tailoring removal

A single PR, clearly labeled, that deletes more code than it adds.

### 4.1 Code deletions

- `backend/app/services/cv_generator.py` — delete file.
- `backend/app/services/cover_letter_generator.py` — delete file.
- `backend/app/api/v1/endpoints/applications.py` — strip to a minimal "saved / applied / dismissed" state tracker. Remove all generation endpoints.
- `frontend/app/dashboard/applications/generate/` — delete the entire subtree (this is also the `dangerouslySetInnerHTML` P1 location).
- `frontend/lib/api/applications.ts` — drop the generation methods.
- Remove `TaskType.CV_TAILORING` and any cover-letter task types from `backend/app/ai/base.py` and `backend/app/ai/router.py`.
- Remove CV generation prompts from any prompt library.
- Drop the docs describing the feature: `docs/AI_CV_GENERATOR_*.md`, `docs/CUSTOM_CV_GENERATION.md`, `docs/CV_TAILORING_*.md`, and the corresponding top-level markdowns that reference them.

### 4.2 Schema changes

Migration `migrations/007_remove_cv_tailoring.sql`:

- Drop columns from `applications`: `tailored_cv_path`, `generation_settings`, `generation_prompt`, `cover_letter_path`, and any other generation-specific fields. Keep: `id`, `user_id`, `job_id`, `cv_id` (nullable), `status`, `created_at`, `updated_at`.
- Trim `applications.status` to `('saved', 'applied_external', 'dismissed', 'hidden')`. Backfill existing rows to `saved`.
- Reconcile into `docs/SUPABASE_SETUP_COMPLETE.sql`.

### 4.3 Storage cleanup

One-time script (`backend/scripts/maintenance/delete_tailored_cvs.py`):

- List all objects in `cvs` bucket under prefix `tailored-cvs/`.
- Delete them all. Log counts per user.
- This closes audit P0.2 simultaneously.

Run under a feature-flag / manual trigger, not automatically on deploy, so it can be reviewed first.

### 4.4 Acceptance checklist

- [ ] `rg cv_generator|cover_letter_generator|tailored_cv` returns 0 hits.
- [ ] `frontend` builds and type-checks.
- [ ] `backend` pytest passes.
- [ ] Fresh DB from `docs/SUPABASE_SETUP_COMPLETE.sql` matches what `migrations/` produces.
- [ ] `tailored-cvs/` prefix in Supabase Storage is empty.

## 5. Recommendation Engine V2

### 5.1 Data model

Additive migration `migrations/008_recommendations_v2.sql`:

- New table `job_embeddings`:
  - `job_id` UUID PK FK → jobs(id) ON DELETE CASCADE.
  - `embedding` `vector(768)` (pgvector, sized for Gemini `text-embedding-004`) or `float8[]` fallback. Widen to `vector(1536)` if you flip the primary provider to OpenAI.
  - `model` TEXT NOT NULL (default `text-embedding-004`; see §3.1). Queries MUST filter by `model`.
  - `source_hash` TEXT NOT NULL (hash of the text we embedded; allows cheap "did this change" checks).
  - `embedded_at` TIMESTAMPTZ NOT NULL DEFAULT NOW().
  - Index: `CREATE INDEX ON job_embeddings USING hnsw (embedding vector_cosine_ops)` if pgvector is enabled.
- New table `user_embeddings`:
  - `user_id` UUID PK.
  - Same shape as `job_embeddings` (same `model` tagging rules apply).
- Extend `job_recommendations`:
  - `tier` TEXT NOT NULL, CHECK `tier IN ('tier1', 'tier2', 'tier3')`. Default `'tier2'`.
  - `semantic_fit` DOUBLE PRECISION NULL.
  - `title_alignment` DOUBLE PRECISION NULL.
  - `skill_overlap` DOUBLE PRECISION NULL.
  - `freshness` DOUBLE PRECISION NULL.
  - `channel_bonus` DOUBLE PRECISION NULL.
  - `interest_affinity` DOUBLE PRECISION NULL.
  - `llm_rerank_score` DOUBLE PRECISION NULL (0–100 from rerank model; NULL if not reranked).
  - `match_reason` TEXT NULL — keep but overwrite with the reranker's one-sentence output.
  - Add FK `user_id` → `users(id)` ON DELETE CASCADE (this closes P2.12 index-drift finding from the audit).

### 5.2 Scoring dimensions

All scores 0.0–1.0 unless noted.

- `semantic_fit` = `cosine(user_embedding, job_embedding)`.
- `title_alignment` — 0.0 no overlap, 0.3 keyword overlap, 0.6 substring match, 1.0 exact match against any target title.
- `skill_overlap` — fraction of user's top-15 skills present in normalized job text (title + first 1500 chars of description).
- `freshness` — piecewise on `posted_date` (fallback to `scraped_at`):
  - ≤48h: 1.0
  - ≤7d:  0.8
  - ≤14d: 0.4
  - older: 0.1
- `channel_bonus` — 1.0 for `source='recruiter'` approved and verified, 0.8 other scraped sources, 0.0 expired or `external`.
- `interest_affinity` — cosine to centroid of the user's last 10 saved/applied jobs' embeddings. If the user has <3 interest signals, set to NULL and ignore.
- `llm_rerank_score` — 0–100, from a single `gemini-1.5-flash` call (primary; see §3.1) over the top 50 candidates, with `gpt-4o-mini` as fallback (see §5.4).

Composite only for ordering within Tier 2 and Tier 3; **tiering itself is rule-based, not a single weighted score** (see §5.3).

### 5.3 Tier rules

Given a candidate pool `C` for a user after candidate selection (§5.5):

- **Tier 1 — Highly Recommended** (cap 10):
  - `llm_rerank_score ≥ 85` AND
  - `freshness ≥ 0.8` AND
  - (`title_alignment ≥ 0.6` OR `skill_overlap ≥ 0.3`)
- **Tier 2 — Likely a Fit** (cap 30):
  - Not in Tier 1 AND
  - (`llm_rerank_score ≥ 60` OR `semantic_fit ≥ 0.55`)
- **Tier 3 — All Roles** (paginated, up to 200 surfaced):
  - Not in Tier 1 or 2 AND
  - Job's normalized title is in the user's target-title cluster (primary + secondary titles broadened by embedding-nearest-neighbor at index time).
  - Default sort: freshness desc, then `semantic_fit` desc.

If Tier 1 is empty after running, do **not** promote Tier 2 picks. Instead surface a UI nudge: "Enrich your profile to see highly recommended roles."

### 5.4 LLM reranker

A single reranker call per user per run. Input: top 50 jobs by `semantic_fit`. Output: JSON array of `{job_id, score, reason}` where `score ∈ [0, 100]` and `reason` is ≤ 20 words.

Prompt skeleton (schematic, do not hardcode PII):

```
You are scoring job fit for a candidate. Given the candidate's target titles, top skills,
and a list of 50 candidate jobs (title + 400-char description + company), return a strict
JSON array [{"job_id": "...", "score": 0-100, "reason": "..."}] ordered by score desc.
Use 85+ only for roles that clearly match the candidate's target title AND use at least
one of their top skills. Use 60-84 for adjacent roles. Never invent facts.
```

Guardrails:

- Truncate each job's description to 400 chars *after* HTML strip.
- Reject and fall back to `semantic_fit` ordering if JSON parse fails or fewer than 30 items returned.
- Hard per-user budget: 1 rerank call per generation. On the Gemini free tier this is $0; on the OpenAI fallback one user's run is ≤ $0.002.
- Route via `app.ai.router`. Never call the provider SDK directly from `RecommendationGenerator`.

### 5.5 Candidate selection

Two-stage retrieval:

1. Postgres query (pgvector):
   ```sql
   SELECT j.id
   FROM jobs j
   JOIN job_embeddings e ON e.job_id = j.id
   WHERE j.scraped_at > NOW() - INTERVAL '7 days'
     AND (j.source != 'external')
     AND (j.moderation_status IS NULL OR j.moderation_status = 'approved')
     AND (j.expires_at IS NULL OR j.expires_at > NOW())
   ORDER BY e.embedding <=> :user_emb
   LIMIT 200;
   ```
   If pgvector is not yet installed, fall back to fetching recent jobs and computing cosine in Python — the rest of the pipeline is unchanged.
2. Apply soft down-ranks (do not exclude):
   - `-10%` if a target-title stack word is present in title but the user's skill list misses it entirely.
   - `-5%` per user `excluded_keywords` hit.
3. Keep the top 50 by `semantic_fit` for the reranker.

Remove the hard exclusion gates in the current `AIJobMatcher` (`JOB_STACK_KEYWORDS_IN_TITLE`, `_job_aligns_with_profile`, `_filter_tech_jobs`). They cause more silent false negatives than real spam reduction.

### 5.6 Pipeline

1. **On job ingestion** (scraper or recruiter post after approval): Celery task `embed_job(job_id)` computes and stores the embedding if `source_hash` changed.
2. **On profile / CV update**: Celery task `embed_user(user_id)` recomputes and stores the user embedding.
3. **Per-user recommendation run** (Celery Beat, every 12h; plus on-demand for new users):
   - Select top 200 by pgvector.
   - Compute all sub-scores in Python.
   - LLM rerank top 50.
   - Classify into tiers.
   - Upsert into `job_recommendations` (replace existing rows for the user).
4. **Read path**: `GET /api/v1/recommendations?tier=tier1|tier2|tier3&page=…`. Returns precomputed rows. No AI at request time.

### 5.7 API changes

- New endpoint `GET /api/v1/recommendations` (replaces `/jobs/recommendations`):
  - Query params: `tier` (required: `tier1|tier2|tier3`), `page`, `page_size`.
  - Response: paginated jobs with `match_score`, `match_reason`, `tier`, and the sub-scores.
- Keep `/jobs/` search as today but drop the `matched=true` branch. That functionality now lives on `/recommendations?tier=tier2`.
- `POST /api/v1/recommendations/regenerate` — current-user trigger; rate-limited (1/hour).

### 5.8 Frontend

- `frontend/app/dashboard/page.tsx` becomes the three-column view.
- On desktop: three columns side by side.
- On mobile: three tabs labeled "Top picks", "Worth a look", "All roles".
- Each card shows: match %, one-line reason, freshness badge, company + optional recruiter-verified badge, Apply button (external `target="_blank" rel="noopener noreferrer nofollow"` per `docs/RECRUITER_JOB_POSTINGS_PLAN.md` §6).
- Empty Tier 1 state explains what signal is missing (no primary title, no skills, no active CV).

## 6. WhatsApp Business delivery

### 6.1 Feature scope for MVP

- Candidate opts in, verifies phone, receives **one Tier-1 digest per day** at their chosen local-time window (default 08:00 local).
- Digest contains up to 5 Tier-1 jobs and a single CTA link back to the platform.
- STOP/UNSUBSCRIBE handled via incoming-message webhook.
- Delivery status (sent / delivered / read / failed) recorded.

Not in MVP: immediate alerts on very high-score matches, in-message quick replies, two-way chat support, other channels (email, SMS, Telegram).

### 6.2 Meta / provider details

- **API**: Meta WhatsApp Cloud API (`graph.facebook.com/v*/{phone_number_id}/messages`).
- **Number**: your existing Business number (via Meta).
- **Templates**: two approved templates, categories as listed.
  - `otp_verification` (category `AUTHENTICATION`) — phone verify.
  - `daily_job_digest` (category `MARKETING`) — the digest.
  - Both templates have to be submitted via Meta Business Manager; approval is 1–24h.
- **Webhook**: single HTTPS endpoint `/api/v1/webhooks/whatsapp` that receives:
  - Delivery status updates.
  - Incoming messages (for STOP handling and OTP reply-based confirmation if ever needed).
- **Verification signature**: Meta sends `X-Hub-Signature-256` HMAC. Always verify before processing.

### 6.3 Data model

Migration `migrations/009_add_whatsapp.sql`:

- New table `notification_preferences`:
  - `user_id` UUID PK FK.
  - `whatsapp_opted_in` BOOLEAN NOT NULL DEFAULT FALSE.
  - `whatsapp_opted_in_at` TIMESTAMPTZ NULL.
  - `whatsapp_opt_in_source` TEXT NULL (`'signup'`, `'profile_page'`).
  - `whatsapp_phone_e164` TEXT NULL (validated E.164, no spaces).
  - `whatsapp_phone_verified_at` TIMESTAMPTZ NULL.
  - `whatsapp_digest_time_local` TEXT NOT NULL DEFAULT `'08:00'`.
  - `whatsapp_timezone` TEXT NOT NULL DEFAULT `'UTC'` (IANA TZ names).
  - `whatsapp_opted_out_at` TIMESTAMPTZ NULL (set when STOP received or user toggles off).
  - `whatsapp_paused_until` TIMESTAMPTZ NULL (soft pause).
  - `updated_at` TIMESTAMPTZ NOT NULL DEFAULT NOW().
- New table `whatsapp_messages`:
  - `id` UUID PK.
  - `user_id` UUID FK (ON DELETE SET NULL so abuse records survive account deletion long enough to be cleaned up by retention policy).
  - `template_name` TEXT NOT NULL.
  - `template_language` TEXT NOT NULL DEFAULT `'en'`.
  - `phone_e164` TEXT NOT NULL.
  - `payload_hash` TEXT NOT NULL (hash of the message content for dedup).
  - `provider_message_id` TEXT NULL.
  - `status` TEXT NOT NULL (`queued`, `sent`, `delivered`, `read`, `failed`, `rate_limited`, `opt_out_blocked`).
  - `error_code` TEXT NULL.
  - `error_message` TEXT NULL.
  - `sent_at` TIMESTAMPTZ NULL.
  - `delivered_at` TIMESTAMPTZ NULL.
  - `read_at` TIMESTAMPTZ NULL.
  - `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW().
- New table `whatsapp_incoming_events`:
  - `id` UUID PK.
  - `phone_e164` TEXT NOT NULL.
  - `user_id` UUID NULL (resolved if phone matches an opted-in record).
  - `type` TEXT NOT NULL (`text`, `status_update`, `button`).
  - `body` TEXT NULL.
  - `raw` JSONB NOT NULL (for debug; redact in response logs).
  - `received_at` TIMESTAMPTZ NOT NULL DEFAULT NOW().

Indexes for `phone_e164`, `user_id`, `status` on the message table.

### 6.4 Opt-in flow

1. User opens a "WhatsApp notifications" section in profile settings.
2. Enters phone number. Client-side library validates E.164 format (country code required).
3. `POST /api/v1/notifications/whatsapp/opt-in` with `{ phone }`. Backend:
   - Rate-limits OTP sends per user (max 3/hour, 10/day).
   - Generates a 6-digit code.
   - Sends the `otp_verification` template via WhatsApp Cloud API.
   - Stores the code hashed in a short-lived Redis key (`wa_otp:{user_id}` TTL 10 min).
4. User enters the code. `POST /api/v1/notifications/whatsapp/verify` with `{ code }`. Backend compares, marks `whatsapp_phone_verified_at = NOW()`, sets `whatsapp_opted_in = TRUE`, stores `whatsapp_opted_in_at`, `whatsapp_opt_in_source`.
5. User can pick digest time and timezone.
6. Profile page shows "Opt out" toggle → clears `whatsapp_opted_in`, sets `whatsapp_opted_out_at`.

### 6.5 Daily digest dispatcher

Celery Beat task `dispatch_whatsapp_digests` runs **hourly**:

1. Compute current local hour per user from `whatsapp_timezone` + `whatsapp_digest_time_local`.
2. Select users whose local digest hour == current UTC hour, `whatsapp_opted_in = TRUE`, verified, not opted-out, not paused.
3. For each user, pull their Tier-1 recommendations (up to 5) from `job_recommendations`. Skip user if zero.
4. Compose the template variables:
   - `{{1}}`: first name (from `users.full_name`, fallback "there").
   - `{{2}}`: bullet list of "• Title — Company (match%)", newline-separated, max 5.
   - `{{3}}`: CTA link — a signed URL to `/dashboard/picks?day=YYYYMMDD&token=…` that auto-logs-in via a short-lived Supabase magic link or JWT.
5. Enqueue one Celery task `send_whatsapp_template(user_id, template, vars, idempotency_key)` per user. Idempotency key = hash of `user_id + date + template`.
6. Worker calls the Cloud API with exponential backoff and per-number rate limiting (token bucket, respecting the user's current messaging tier).
7. On success: record `provider_message_id`, set `status='sent'`.
8. On `131026` (template not approved) / `131047` (re-engagement required) / etc: mark `status='failed'`, log; do not retry automatically — alert Ops.

### 6.6 Incoming webhook

- Verify Meta's `X-Hub-Signature-256` HMAC against app secret.
- For `statuses` events: update `whatsapp_messages.status`, `delivered_at`, `read_at`.
- For incoming `messages` events:
  - Record in `whatsapp_incoming_events`.
  - If the body (case-insensitive, trimmed) matches any of `STOP`, `UNSUBSCRIBE`, `STOPALL`, `OPTOUT`, `END`, `CANCEL`:
    - Set `notification_preferences.whatsapp_opted_in=FALSE`, `whatsapp_opted_out_at=NOW()`.
    - Reply once with a fixed confirmation template (`unsubscribe_confirmation`) if Meta's 24h customer-service window is open; otherwise no reply.
  - If `START` / `RESUME` / `SUBSCRIBE` arrives and the user was previously opted-in: reactivate (but do not create an opt-in from scratch — phone must be verified).

### 6.7 Compliance and audit

- Every opt-in and opt-out event is logged to `whatsapp_incoming_events` or a dedicated audit trail with timestamp and source. Keep 7 years (regulatory minimum in many jurisdictions).
- Never store raw OTPs — hash them.
- Never send marketing templates to unverified or opted-out users. Enforce in `send_whatsapp_template`, not just at dispatcher level.
- Respect the **24-hour customer service window** rule: free-form responses only within 24h of a user-initiated message. Otherwise only pre-approved templates.
- STOP keywords honored within the same webhook call (no async delay).

### 6.8 Budget and rate-limit guardrails

- New config values (no secrets, just limits):
  - `WHATSAPP_MAX_SENDS_PER_DAY` (global, default 5000 — well under your tier cap).
  - `WHATSAPP_MAX_SENDS_PER_USER_PER_DAY` (default 1).
  - `WHATSAPP_PROVIDER_RPS` (default 5, per Meta's default 80 messages/sec for your tier; keep lots of headroom).
- Budget circuit breaker: if today's send count hits `WHATSAPP_MAX_SENDS_PER_DAY`, pause the dispatcher and alert Ops.

### 6.9 New secrets (add to `.env.example`, never commit)

- `WHATSAPP_APP_ID`
- `WHATSAPP_APP_SECRET` (used for HMAC on webhook)
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_VERIFY_TOKEN` (used by Meta during webhook verification handshake)

### 6.10 Templates to submit to Meta

| Template | Category | Language | Variables | Purpose |
|---|---|---|---|---|
| `otp_verification` | AUTHENTICATION | en | `{{1}}` code | Phone verification during opt-in |
| `daily_job_digest` | MARKETING | en | `{{1}}` name, `{{2}}` job list, `{{3}}` CTA URL | The Tier-1 digest |
| `unsubscribe_confirmation` | UTILITY | en | none | Confirm STOP received |

Submit templates at the start of Phase 2 so approval (1–24h) overlaps with implementation work.

## 7. Phased task list

Each phase is a self-contained PR and can be reviewed independently. Phases can run in parallel with the recruiter-postings plan.

### Phase 0 — Decision + removal (1–2 days)

- [ ] Confirm open questions (§9).
- [ ] Write `migrations/007_remove_cv_tailoring.sql`.
- [ ] Delete `cv_generator.py`, `cover_letter_generator.py`, related endpoints, frontend pages (§4.1).
- [ ] Script `backend/scripts/maintenance/delete_tailored_cvs.py` to wipe `tailored-cvs/` prefix.
- [ ] Run full backend test suite; ensure no references remain.
- [ ] Update `README.md`, remove tailoring docs.

### Phase 1 — Recommendations V2 backend (3–5 days)

- [ ] `migrations/008_recommendations_v2.sql` with `job_embeddings` (`vector(768)`), `user_embeddings`, and `job_recommendations` column additions.
- [ ] Reconcile in `docs/SUPABASE_SETUP_COMPLETE.sql`.
- [ ] Install pgvector in Supabase (one-time) or ship with the float8[] fallback.
- [ ] Extend `app.ai.router` with explicit `embed(task, texts)` and `rerank(...)` entry points; wire Gemini as primary, OpenAI as fallback per §3.1.
- [ ] Add `AI_EMBEDDING_PROVIDER`, `AI_EMBEDDING_MODEL`, `AI_RERANK_PROVIDER`, `AI_RERANK_MODEL`, `AI_PROVIDER_FALLBACK_ENABLED` to `.env.example` and `app/core/config.py`.
- [ ] Celery tasks `embed_job(job_id)` and `embed_user(user_id)`, both reading provider config from the router and tagging rows with `model`.
- [ ] Hook into scraper pipeline and profile/CV update paths so new content triggers re-embed.
- [ ] Rewrite `RecommendationGenerator` around the pipeline in §5.6. Drop hard-exclusion gates. Filter `job_embeddings` and `user_embeddings` by `model`.
- [ ] Implement LLM reranker via `app.ai.router` with the prompt in §5.4; graceful fallback to `semantic_fit` ordering when both providers fail.
- [ ] Tier classification in SQL or Python; write results with `tier` column.
- [ ] New endpoint `GET /api/v1/recommendations?tier=`; deprecate `/jobs/recommendations` behind a 307 redirect for one release.
- [ ] Unit and integration tests for tiering, embedding cache reuse, rerank JSON parse failure, empty Tier-1 path, provider fallback path.

### Phase 2 — Scheduler migration (1–2 days) — **DONE**

- [x] Port APScheduler jobs in `backend/app/scheduler/job_scheduler.py` to Celery Beat tasks in `backend/app/tasks/periodic_tasks.py`.
- [x] Delete `app.scheduler` package; remove its start/stop from `main.py` lifespan.
- [x] Document the Celery Beat command in `docs/deployment/CELERY.md`.
- [x] Add `SCHEDULER_MODE` flag (`celery` | `disabled`) as a safety switch.
- [x] Add smoke test (`tests/test_periodic_tasks.py`) asserting the Beat schedule.

### Phase 3 — Frontend 3-tier UI (2–3 days)

- [ ] Replace the current `/dashboard` page with the three-column (desktop) / three-tab (mobile) view.
- [ ] New `frontend/lib/api/recommendations.ts` client matching the new endpoint.
- [ ] Empty-state design for Tier 1 with a profile-enrichment nudge.
- [ ] Kill the old `applications/generate` subtree.
- [ ] `npm run type-check` and `npm run build` pass.

### Phase 4 — WhatsApp foundation (3–5 days)

- [ ] Submit the three Meta templates for approval (do first; overlaps with code work).
- [ ] `migrations/009_add_whatsapp.sql` for `notification_preferences`, `whatsapp_messages`, `whatsapp_incoming_events`.
- [ ] Config + secrets in `.env.example`.
- [ ] `backend/app/services/whatsapp_client.py` — thin wrapper around the Cloud API (`send_template`, `verify_webhook_signature`).
- [ ] Endpoints: `POST /notifications/whatsapp/opt-in`, `POST /notifications/whatsapp/verify`, `POST /notifications/whatsapp/opt-out`, `GET /notifications/whatsapp/status`.
- [ ] Webhook endpoint `POST /webhooks/whatsapp` with signature verification, STOP handling, status-update persistence.
- [ ] Frontend: profile settings panel for WhatsApp — phone input, verify code box, digest time, timezone picker, opt-out toggle.
- [ ] Rate limits on OTP sends.

### Phase 5 — WhatsApp digest dispatcher (2 days)

- [ ] Celery Beat hourly task `dispatch_whatsapp_digests`.
- [ ] Celery worker task `send_whatsapp_template` with idempotency, backoff, budget circuit breaker.
- [ ] Signed-link generator for the CTA URL (short-lived JWT or Supabase magic link).
- [ ] Admin endpoint `GET /admin/whatsapp/stats` — daily sends, delivery rate, opt-out rate.
- [ ] End-to-end test: opt-in user with one Tier-1 rec receives the template; STOP reply flips opt-in; next day's dispatcher skips them.

### Phase 6 — Hardening (ongoing, 1 week)

- [ ] Observability: structured logs with request_id, user_id (hashed), provider_message_id.
- [ ] Alerts on: delivery rate <80%, opt-out rate >5% in a day, template failures >3 per hour.
- [ ] Load test the recommendation generation at 10k users (use the embedding cache path).
- [ ] Document incident runbook for "WhatsApp number suspended" (Meta will do this if quality drops).

## 8. Testing plan

### 8.1 Backend

- Tiering correctness: synthetic jobs with known sub-scores should classify into the expected tier every time.
- Empty Tier 1 path: user with no skills/title gets empty Tier 1 and non-empty Tier 3.
- LLM rerank fallback: mock the router to return malformed JSON; pipeline still produces tiers ordered by `semantic_fit`.
- Embedding cache reuse: running generator twice without changing profile or jobs must issue zero OpenAI calls on the second run.
- WhatsApp webhook HMAC: requests without valid signature return 403; valid STOP flips opt-in state.
- Idempotency: re-running the dispatcher for the same day does not double-send.

### 8.2 Frontend

- `npm run type-check` and `npm run build` pass.
- Three-column view renders with tier-specific empty states.
- WhatsApp settings panel: phone input validates E.164; verify flow accepts a 6-digit code and rejects otherwise.

### 8.3 Migration

- Fresh-database bootstrap from `docs/SUPABASE_SETUP_COMPLETE.sql` == sequential run of `migrations/` == current models.
- Explicit test for `applications` status enum change (old values backfilled to `saved`).

## 9. Open product questions

Defaults in parentheses. Please confirm or override before Phase 0 merges.

1. Is deleting (vs archiving) `cv_generator.py` and the tailored-CV files in Storage acceptable? (Default: delete.)
2. Daily digest cadence vs weekly? (Default: daily at user-local 08:00; opt for weekly in profile if they prefer.)
3. How many jobs per WhatsApp digest? (Default: 5.)
4. Tier 3 scope: user's target category only, or the entire job catalog? (Default: target category, broadened by embedding neighbors.)
5. Immediate alerts on very high-score matches (e.g., cosine ≥ 0.85)? (Default: not in MVP.)
6. Fallback channel if a candidate does not opt in to WhatsApp — do we want email digests too? (Default: not in MVP; consider Phase 7.)
7. Which locales/languages are in scope? (Default: `en` only; templates approved in one language first.)
8. Who is the "admin" that approves recruiter jobs and reviews WhatsApp stats — same person? (Default: yes, single `role='admin'` for now.)
9. Confirm Gemini as primary for both embeddings and rerank, with OpenAI as paid fallback? (Default: yes; §3.1.)
10. Keep an OpenAI fallback at all, or go Gemini-only and fail loudly when Gemini is down? (Default: keep OpenAI fallback for the first 30 days, then revisit based on `fallback_success` counter.)

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| LLM rerank hallucinates or returns bad JSON. | Strict schema validation; fall back to `semantic_fit` order; cap per-user budget. |
| Gemini free tier rate-limits the dispatcher during peak hours. | Router retries with jittered backoff once, then fails over to OpenAI if `AI_PROVIDER_FALLBACK_ENABLED`; per-task counters alert when fallback-rate > 10% for a day. |
| Provider switch invalidates cached vectors. | `job_embeddings.model` tags every row; queries filter by `model`; provider flip = enqueue a one-time re-embed job over active jobs + users. |
| WhatsApp number quality score drops, sends throttled. | Send only Tier-1 quality picks; honor STOP instantly; hourly budget circuit breaker; daily quality-metric alert. |
| Meta template rejection delays launch. | Submit templates on day 1 of Phase 4; implement code paths against mocked responses in the meantime. |
| Users upload phone numbers they don't control. | OTP verification is required before any marketing message is sent; OTP is the only pre-verification template. |
| Removing CV tailoring strands user data. | Phase 0 includes an explicit one-time storage cleanup with logging. |
| pgvector not available in the Supabase tier being used. | Float8[] fallback path is wired in for Phase 1; upgrade later without pipeline changes. |
| Celery Beat + APScheduler run in parallel during migration. | Phase 2 is a single-atomic switch: delete APScheduler start from `main.py` in the same PR that wires Celery Beat. |

## 11. Alignment with other plans and audit

- `docs/RECRUITER_JOB_POSTINGS_PLAN.md`: recruiter jobs are simply another `source` in the pipeline here. Tier classification treats them identically; they get the `channel_bonus`.
- `docs/PRODUCTION_SYSTEM_AUDIT_2026-04-18.md`:
  - P0.2 (public CV URLs) is closed by §4.3 storage cleanup.
  - P1.5 (`dangerouslySetInnerHTML`) is closed by deleting `applications/generate/[jobId]`.
  - P1.10 (partial prompt injection defenses) is largely closed by removing the tailoring prompt path.
  - P1.11 (scheduler duplication) is closed by Phase 2.
  - P2.12 (index / FK drift on `job_recommendations`) is closed by Phase 1's migration.
- `AGENTS.md` / `CLAUDE.md` engineering rules: every new endpoint filters by `current_user["id"]`; recruiter auto-send exclusion honored before any provider call; no rendering of AI-derived text as HTML.
