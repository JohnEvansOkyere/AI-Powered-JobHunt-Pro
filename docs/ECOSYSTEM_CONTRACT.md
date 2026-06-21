<!--
  ╔══════════════════════════════════════════════════════════════════════════╗
  ║  SYNCED FILE — IDENTICAL COPY IN BOTH REPOS. EDIT BOTH OR NEITHER.        ║
  ║  • AI-JOb-Assistant/docs/ECOSYSTEM_CONTRACT.md        (VeloxaRecruit/ATS) ║
  ║  • AI-Powered-JobHunt-Pro/docs/ECOSYSTEM_CONTRACT.md  (VeloxaHire)        ║
  ║  When you change one, copy the change to the other in the SAME session    ║
  ║  and bump "Contract version" + add a row to the Synced Change Log.        ║
  ╚══════════════════════════════════════════════════════════════════════════╝
-->

# Veloxa Ecosystem Contract

**Contract version:** 2026-06-21.7
**Last synced:** 2026-06-21
**Authoritative for:** the cross-repo integration handshake between VeloxaRecruit (ATS) and VeloxaHire (candidate platform).

> **Why this file exists.** The two products are built in two separate repos, each with its own
> `CLAUDE.md`, `MEMORY.md`, and agent sessions (Claude *and* Codex). Before this file, the
> integration was documented asymmetrically — richly on the ATS side, only inside `MEMORY.md` on the
> VeloxaHire side — and the two views had already drifted (see **§9 Drift Watch**). This file is the
> **single source of truth for the things both sides must agree on.** It is copied **byte-identical**
> into both repos. If the two copies ever differ, that is a bug.
>
> This document satisfies the "token contract" deliverable of Phase 3.1 in the ATS
> `docs/architecture/ECOSYSTEM_UNIFICATION_CHECKLIST.md`.

---

## 0. How to use this file (read first)

- **If you are a new Claude/Codex session:** read this whole file before touching any
  integration code (job sync, handoff token, apply flow, shared env/secrets). It tells you what is
  canonical, what is mirrored, and what will break the *other* repo if you change it.
- **The golden invariants** (never violate without Evans saying yes in the same message):
  1. **Never gate `/apply` behind login.** Frictionless apply protects the paying recruiter's
     applicant count. Registration is always *after* apply and *optional*.
  2. **Never merge the two databases.** Consolidate *identity*, not *data*. Each app keeps its own
     DB. VeloxaHire stores a **projection** of ATS jobs and **never writes into ATS tables**.
  3. **Hard stops** — do NOT do these without explicit in-session confirmation: run a DB migration,
     change env/secrets, deploy/reload any server, send real email, touch production data.
- **When you change anything in §3–§7 (the contract surface):** update **both repo copies** in the
  same session, bump **Contract version**, and append to **§10 Synced Change Log**.

---

## 1. The two products

| | Repo | Role | Canonical owner of |
|---|---|---|---|
| **VeloxaRecruit** (ATS) | `AI-JOb-Assistant/` | Recruiter platform: job creation, CV screening, AI interviews, hiring pipeline. The **paying** product. | Recruiter-created **jobs** and **applications** to those jobs |
| **VeloxaHire** | `AI-Powered-JobHunt-Pro/` | Candidate platform: job board, search, recommendations, CV tools. Browse-first front door. | Scraped jobs, candidate profiles, recommendations, **mirror** of published ATS jobs |

The products are **not** being collapsed into one system. They are **connected into one ecosystem**:
ATS is canonical; VeloxaHire mirrors and deep-links back. Repos live side by side at
`Projects/AI-JOb-Assistant/` and `Projects/AI-Powered-JobHunt-Pro/`.

---

## 2. Current state — what is DONE vs WIP vs DEFERRED

Status as of the contract version date. Source: ATS
`docs/architecture/ECOSYSTEM_UNIFICATION_CHECKLIST.md` (the executable build plan) + verified code.

### DONE (shipped on the `feat/ecosystem-unification` branch, not all in production yet)

- **Phase 0 — VeloxaHire is browse-first.** Anonymous users can browse/search/view jobs and open
  public apply links. Signup is the upgrade (saved jobs, tracking, AI shortlist, CV tools), not the
  gate. Public job list + SEO-indexed detail pages exist.
- **Phase 1 — Post-apply capture CTA.** ATS apply success screen links applicants to VeloxaHire's
  job board after the application is already submitted. No PII in the link, no silent account
  creation. (See §5.)
- **Phase 1.5 — Sync observability.** VeloxaHire persists last sync outcome and exposes ops
  endpoints (status + manual backfill). (See §3.)
- **Phase 2 — Pre-filled handoff.** ATS mints a signed short-lived handoff token after apply;
  VeloxaHire verifies it server-side and pre-fills signup (email read-only when prefilled). (See §4.)
- **Phase 3.0 — Auth-only identity foundation scaffold.** VeloxaHire now has a code scaffold for
  separate **auth** vs **data/storage** configuration, but this is **not the final one-login cutover**
  until the Recruit-owned auth broker/provisioning flow in §6 is implemented. Do not set shared-auth
  env in production as a substitute for that broker.
- **Unified front door without unified auth.** VeloxaRecruit now routes job seekers to VeloxaHire
  jobs, and VeloxaHire routes employers to VeloxaRecruit request access. This is the approved
  near-term product architecture: shared navigation, separate logins. (See §5.)

### WIP / on the same branch but unrelated to the ecosystem loop

- **Conversational interview** (Cartesia Sonic TTS + Ink STT). ATS-only product surface (camera/mic,
  uploads, migrations `069`/`070`, replay UI). Flag-gated `CONVERSATIONAL_INTERVIEW_ENABLED`
  (default off). **Increases release blast radius of this branch** — see §9. Not part of this
  contract; listed only so a session knows it is in the branch.

### DEFERRED (decided, not built)

- **Phase 2.4** — carry the CV across at handoff (undecided).
- **Phase 3.1 — Existing VeloxaHire user migration.** Existing VeloxaHire Auth users still need a
  claim-account / magic-link / password-reset migration into canonical VeloxaRecruit Auth. Do not
  delete the old VeloxaHire auth user pool until this is complete. (See §6.)
- **Phase 4** — application status callbacks to VeloxaHire; in-VeloxaHire apply UX (kill the
  deep-link seam); job-publication webhooks from ATS.

---

## 3. CONTRACT — Job sync (ATS → VeloxaHire)

ATS publishes a candidate-safe projection of published jobs; VeloxaHire pulls and upserts it. **The
candidate mirror is never canonical.**

**ATS side (producer)** — `backend/app/api/published_jobs.py`, `services/published_job_service.py`:
- Endpoint: `GET /integrations/published-jobs`
- Query params: `updated_since` (ISO datetime, optional), `limit` (1–500, default 500)
- Auth header: **`X-Candidate-Sync-Token`**, compared with `hmac.compare_digest`
- Response: `Response[PublishedJobsSyncPayload]` — candidate-safe fields + lifecycle
  `publication_status` of `published` / `hidden` (hidden = lifecycle tombstone, archived from
  active discovery)
- Public apply URL embedded per job: `{ATS_frontend_url}/apply/{job_id}`

**VeloxaHire side (consumer)** — `backend/app/services/ats_job_sync_service.py`:
- Scheduled by Celery Beat: `backend/app/tasks/periodic_tasks.py` → `scheduler.sync_ats_jobs`,
  **every 10 minutes**
- Enabled by env: `ATS_SYNC_ENABLED=true` + `ATS_PUBLISHED_JOBS_URL` + `ATS_SYNC_TOKEN`
- Upserts mirrored jobs with: `source='recruiter'`, `origin_system='ats'`, `origin_job_id`,
  `origin_updated_at`, `ats_organization_id`, `organization_name`, `organization_logo_url`,
  `publication_status`. Stores apply URL as the job's `job_link` / `source_url`.
- Overlap strategy: requests `updated_since = max(origin_updated_at) - 60s`
- Ops endpoints: `GET /api/v1/ops/ats-sync/status` (last run / counts / `stale` flag),
  `POST /api/v1/ops/ats-sync/backfill` (force immediate sync)

**Shared secret (must match across repos):** the sync token.
- ATS env var: **`CANDIDATE_SYNC_TOKEN`**
- VeloxaHire env var: **`ATS_SYNC_TOKEN`**
- Same value, different name. Rotate together.

**Known contract gaps (do not regress; fix before scale):**
- No pagination cursor — only `limit=500`. If >500 jobs share one `updated_at`, sync can replay the
  first page and starve later rows. Add `(updated_at, id)` cursor + `has_more`/`next_cursor` and make
  VeloxaHire loop until drained before scaling the catalog.
- Sync only fires if Celery **worker + beat** are actually running. On a runtime without a persistent
  worker, jobs silently stop mirroring. Treat web + worker + beat as three required processes and
  monitor `/api/v1/ops/ats-sync/status` for `stale=true`.

---

## 4. CONTRACT — Handoff token (ATS apply → VeloxaHire signup)

A signed, short-lived JWT carries applicant prefill from ATS to VeloxaHire signup. **No raw PII in
the URL** — only the opaque token (`?h=<jwt>`).

**Fixed claims (must be identical on both sides):**

| Claim | Value | ATS constant | VeloxaHire constant |
|---|---|---|---|
| `iss` (issuer) | `veloxarecruit` | `HANDOFF_TOKEN_ISSUER` | `HANDOFF_TOKEN_ISSUER` |
| `aud` (audience) | `veloxahire` | `HANDOFF_TOKEN_AUDIENCE` | `HANDOFF_TOKEN_AUDIENCE` |
| `purpose` | `ats_apply` | `HANDOFF_TOKEN_PURPOSE` | `HANDOFF_TOKEN_PURPOSE` |
| algorithm | `HS256` | — | — |
| TTL | **15 minutes** | `create_handoff_token` | enforced via `exp` |

**Payload fields:** applicant `email`, `name`, `phone`, `job` id, `application` id, plus `jti`.
(No CV is carried — Phase 2.4 deferred.)

**ATS side (minter)** — `backend/app/utils/auth.py`:
- `create_handoff_token()` / `decode_handoff_token()`
- Secret: **`HANDOFF_TOKEN_SECRET`**; rotation grace via **`PREVIOUS_HANDOFF_TOKEN_SECRET`**

**VeloxaHire side (verifier)** — `backend/app/api/v1/endpoints/auth.py`:
- Endpoint: `POST /api/v1/auth/handoff/verify` → `HandoffVerifyResponse` (safe prefill fields)
- **Rate-limited** via `HANDOFF_VERIFY_RATE_LIMIT`
- **Single-use:** `_consume_handoff_jti()` atomically marks `handoff:jti:{jti}` in Redis for the
  token's remaining lifetime
- Validates `aud`, `iss`, and `purpose == ats_apply`; honors `PREVIOUS_HANDOFF_TOKEN_SECRET`
- Signup email is read-only in the UI when prefilled

**Shared secret (must match across repos):** **`HANDOFF_TOKEN_SECRET`** (and
`PREVIOUS_HANDOFF_TOKEN_SECRET` only during a short rotation window). If this leaks, an attacker can
mint valid prefill tokens for either backend. Rotate on both backends together.

---

## 5. CONTRACT — The apply loop (already closed)

The candidate→recruiter loop does **not** need a return-path API. It is closed by deep-link:

1. Recruiter creates/updates a job in ATS → ATS stores the canonical job.
2. VeloxaHire sync (§3) mirrors it onto the candidate job board (`source='recruiter'`).
3. Candidate clicks **Apply** on VeloxaHire → routed to the ATS public apply page
   (`{ATS_frontend}/apply/{job_id}`).
4. ATS `POST /applications/apply` inserts the **canonical** application and returns the public
   application response **including the handoff token** (§4).
5. ATS apply success screen shows "other jobs" + a CTA to VeloxaHire's board
   (`{origin}/jobs`, or with handoff `{origin}/register?h=<token>`, where `{origin}` is the bare
   origin of `NEXT_PUBLIC_VELOXAHIRE_URL`).

**Cross-repo env the CTA depends on (ATS frontend):** `NEXT_PUBLIC_VELOXAHIRE_URL` — must be set in
ATS production (Vercel) or the CTA does not render.

**Public apply response is narrowed (RESOLVED 2026-06-21).** `PublicJobApplication`
(`backend/app/models/job_application.py`) no longer inherits the full application shape; it now
exposes only `{application_id, received, handoff_token}`. Internal ids (`candidate_id`, `cv_id`,
`recruiter_owner_id`) and all `pre_screen_*` / decision / pipeline state are no longer returned to
the anonymous applicant. **Do not re-widen this model.**

**Front-door routing (approved near-term UX):**
- VeloxaRecruit is the employer/recruiter entry point. Its landing page should show explicit
  choices:
  - "I'm hiring" → VeloxaRecruit request access / get started
  - "I'm looking for a job" → VeloxaHire `/jobs`
- VeloxaHire is the candidate entry point. Its landing page should show an employer CTA:
  - "Create job for free" → VeloxaRecruit request access / get started
- This is not shared auth. It is honest ecosystem navigation while auth remains separate.
- Safe wording: "connected Veloxa ecosystem", "create a free VeloxaHire profile", "post jobs for
  free on VeloxaRecruit".
- Avoid until §6 broker exists: "one login", "one account", "single sign-on", "use the same account".

---

## 6. CONTRACT — Identity (auth-only unification)

**Decision:** VeloxaRecruit's existing auth stack is the canonical identity path for the ecosystem.
Do **not** replace or simplify VeloxaRecruit auth. It already works and remains the source of truth.
VeloxaHire must integrate with that path while keeping its own database and storage project for
candidate product data.

**Non-negotiable boundary:** this is **not** a database merge.
- VeloxaRecruit remains canonical for recruiter accounts, recruiter jobs, applications, interviews,
  CV screening, and billing/usage tied to recruiters.
- VeloxaHire remains canonical for candidate profiles, saved jobs, recommendations, scraped jobs,
  CV tooling, and mirrored ATS job projections.
- The shared identity key is the VeloxaRecruit user UUID (`sub` / `users.id`) produced by the
  existing Recruit auth flow.

**VeloxaRecruit side (canonical auth owner, do not break):**
- Uses the existing Supabase setup:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
  - `SUPABASE_SERVICE_KEY`
  - `DATABASE_URL`
- Existing signup/login uses Supabase Auth through `db.client.auth.sign_up()` /
  `db.client.auth.sign_in_with_password()`, then Recruit backend applies its own profile/status,
  organization, approval, email-verification, rate-limit, cookie, and CSRF rules.
- Recruit backend issues the app session used by ATS APIs. That session is an implementation detail
  of Recruit and must not be bypassed by VeloxaHire.
- Do not change Recruit's working recruiter auth behavior to make VeloxaHire fit. Add integration
  around it instead.

**Correct one-login design:**
- Add a Recruit-owned auth broker / SSO-style bridge that reuses the existing Recruit auth stack.
- VeloxaHire should send users to that Recruit-owned login/signup path or call a Recruit-owned auth
  API designed for ecosystem login.
- After successful auth, VeloxaHire receives a short-lived, one-time code/token from Recruit and
  exchanges it server-to-server for the shared user identity.
- VeloxaHire then creates/updates its own candidate profile keyed by that shared Recruit user id.
- Because `veloxarecruit.com` and `veloxahire.com` are different root domains, do not assume a
  browser cookie set for one domain can authenticate the other. Use redirect/code exchange or a
  VeloxaHire-owned session derived from a Recruit-issued one-time code.

**What is NOT sufficient:**
- Do not merely point VeloxaHire's frontend `supabase-js` signup/login at the Recruit Supabase
  project. That can bypass Recruit backend checks and create orphaned Supabase Auth users without
  the required Recruit `users` profile/status records.
- Do not make VeloxaHire write directly into Recruit auth/profile tables.
- Do not share Recruit service-role credentials with the VeloxaHire frontend.

**VeloxaHire side (auth consumer, data owner):**
- A temporary config scaffold exists:
  - frontend `NEXT_PUBLIC_AUTH_SUPABASE_URL`
  - frontend `NEXT_PUBLIC_AUTH_SUPABASE_ANON_KEY`
  - backend `AUTH_SUPABASE_URL`
  - backend `AUTH_SUPABASE_KEY`
  - backend `AUTH_SUPABASE_JWT_SECRET`
- Treat that scaffold as incomplete unless it is backed by Recruit-owned provisioning/broker logic.
  Do not use it alone as the production one-login cutover.
- VeloxaHire data/storage still use:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
  - `SUPABASE_SERVICE_KEY`
  - `SUPABASE_STORAGE_BUCKET`
  pointed at the VeloxaHire Supabase project.

**Capability model (required before relying on one login for access control):**
- A shared user can be candidate-only, recruiter-only, or both.
- Do not infer recruiter access merely from having a shared auth account.
- Add server-controlled capability flags or an app table keyed by shared `user_id`, for example:
  `is_candidate`, `is_recruiter`, `organization_id`, `role`.

**Handoff after shared auth cutover:**
- The handoff token (§4) still exists, but its job changes from "prefill a separate VeloxaHire
  signup" to "carry apply context into the shared signup/login flow."
- After signup/login/code exchange, VeloxaHire should create or update the candidate profile using
  the shared VeloxaRecruit user id.

**Existing-user migration warning:**
- Existing VeloxaHire Auth passwords cannot be silently copied into VeloxaRecruit Auth.
- Use a claim-account, magic-link, or password-reset migration flow.
- Keep the old VeloxaHire auth pool read-only/available for migration lookup until the migration is
  complete and verified.

---

## 7. CONTRACT — Shared secrets & migration coupling

**Secrets that MUST be identical across the two deployments** (set only in deployment secret stores,
never long-lived local `.env`):

| Purpose | ATS env var | VeloxaHire env var |
|---|---|---|
| Job-sync bearer token | `CANDIDATE_SYNC_TOKEN` | `ATS_SYNC_TOKEN` |
| Handoff signing secret | `HANDOFF_TOKEN_SECRET` | `HANDOFF_TOKEN_SECRET` |
| Handoff rotation grace | `PREVIOUS_HANDOFF_TOKEN_SECRET` | `PREVIOUS_HANDOFF_TOKEN_SECRET` |

**Auth-only scaffold env (VeloxaHire only; not enough for production one-login by itself):**

| Purpose | VeloxaHire backend env | VeloxaHire frontend env |
|---|---|---|
| Canonical auth project URL | `AUTH_SUPABASE_URL` | `NEXT_PUBLIC_AUTH_SUPABASE_URL` |
| Canonical auth anon key | `AUTH_SUPABASE_KEY` | `NEXT_PUBLIC_AUTH_SUPABASE_ANON_KEY` |
| Canonical auth JWT secret | `AUTH_SUPABASE_JWT_SECRET` | — |

Keep VeloxaHire `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, and
`SUPABASE_STORAGE_BUCKET` pointed at the VeloxaHire data/storage project. Do not set the auth
scaffold env in production until the Recruit-owned broker/provisioning flow in §6 is implemented.

**Cross-repo URL env:** ATS frontend needs `NEXT_PUBLIC_VELOXAHIRE_URL`; VeloxaHire frontend needs
`NEXT_PUBLIC_VELOXARECRUIT_URL`; VeloxaHire backend needs `ATS_PUBLISHED_JOBS_URL`.

> **RULE — the two landing nav env vars hold the FULL destination URL (incl. path), used verbatim.**
> - `NEXT_PUBLIC_VELOXAHIRE_URL=https://<hire-host>/jobs` — ATS landing "looking for a job" links here as-is.
> - `NEXT_PUBLIC_VELOXARECRUIT_URL=https://<recruit-host>/register` — VeloxaHire landing "I'm hiring" links here as-is.
>
> Code no longer appends a path for these buttons; whatever you put in the env var is exactly where
> users land. To change a destination, edit the Vercel env var and redeploy — no code change.
>
> **Exception — the post-apply handoff** (`apply/[jobId]/page.tsx`) reuses `NEXT_PUBLIC_VELOXAHIRE_URL`
> but needs `…/register?h=<token>`, so it derives the **origin** from that var (`new URL(x).origin`)
> and appends `/register?h=`. That's why `NEXT_PUBLIC_VELOXAHIRE_URL` can safely carry the `/jobs`
> path: the nav button uses it whole, the handoff strips to origin. The `?h=<token>` is per-applicant
> and therefore must stay in code.
>
> History: a prod bug where the env had a path AND code appended another produced `/jobs/jobs` and
> `/register/get-started`; fixed 2026-06-21 by making nav links use the env var verbatim.

**Migration coupling:**
- VeloxaHire ecosystem migrations: **`010_add_ats_job_mirroring.sql`**,
  **`011_allow_recruiter_source.sql`**, and **`012_drop_jobs_source_check.sql`**. Migration `012`
  removes the brittle fixed-list `jobs.source` database check so new source labels do not require a
  schema migration.
- ATS conversational migrations `069`/`070` are **not** part of this contract (separate feature).

**Rotation playbook (summary):** rotate the sync token pair together; rotate `HANDOFF_TOKEN_SECRET`
on both backends, setting the old value as `PREVIOUS_HANDOFF_TOKEN_SECRET` only for a short grace
window, then remove it. Never log these headers/secrets.

---

## 8. Minimum release gate (before calling the ecosystem "live")

From the 2026-06-21 danger audit. Do not launch the unified ecosystem until all are true:

1. Shared sync/handoff/payment/provider secrets rotated and held only in deployment secret stores.
2. VeloxaHire migrations `010` + `011` + `012` applied (ATS conversational migrations only if that
   feature ships).
3. VeloxaHire web + Celery worker + Celery Beat all confirmed running.
4. `/api/v1/ops/ats-sync/status` shows a recent **scheduled** success (`last_trigger=scheduled`).
5. VeloxaHire auth unification uses a Recruit-owned broker/provisioning flow and does not bypass
   Recruit's existing backend auth/profile/status checks.
6. VeloxaHire `SUPABASE_*` still points at VeloxaHire data/storage. Any `AUTH_SUPABASE_*` scaffold
   env is backed by the broker flow and is not used alone as a direct Supabase-login cutover.
7. Focused ATS tests run in a **project-local** backend venv (global Anaconda Python has an
   incompatible `supabase` import surface — not a valid verification environment).
8. Focused VeloxaHire tests run from `backend/`.
9. Conversational-interview WIP isolated or its flag/migrations/buckets/billing verified.
10. Public ATS apply response narrowed (§5). ✅ DONE 2026-06-21.
11. Sync pagination cursor added before scaling the catalog (§3).
12. Existing VeloxaHire user migration plan documented before retiring the old VeloxaHire auth pool.

---

## 9. Drift Watch — known doc/code mismatches

Keep this section honest. When you reconcile an item, move it to the Change Log.

- **Handoff single-use + rate limit:** the 2026-06-21 danger audit (P1 #7) states the handoff token
  is *not* single-use and verify is *not* rate-limited. **The code contradicts this** — VeloxaHire
  already implements `_consume_handoff_jti` (Redis `handoff:jti:{jti}`) and `HANDOFF_VERIFY_RATE_LIMIT`
  (`backend/app/api/v1/endpoints/auth.py`). Treat §4 above as current truth; the audit is stale on
  this point.
- **Doc asymmetry (the reason this file exists):** ATS has five ecosystem docs under
  `docs/architecture/` + `docs/memory/`; VeloxaHire previously had the integration only inside
  `MEMORY.md`. This file is now the shared spine; the others remain repo-specific detail.

---

## 10. Synced Change Log (append-only — copy each row into BOTH repos)

| Date (UTC) | Contract version | Change | By |
|---|---|---|---|
| 2026-06-21 | 2026-06-21.7 | Simplified the two landing nav buttons to use the env var **verbatim** (Evans: "just sending them to the next page, make it easy"). [ATS] `LandingPageClient.tsx` → `NEXT_PUBLIC_VELOXAHIRE_URL` used as-is (set it to the full `…/jobs` URL); [HIRE] `app/page.tsx` → `NEXT_PUBLIC_VELOXARECRUIT_URL` used as-is (full `…/register` URL). Removed the `siteOrigin()` helper from both. Destination is now fully env-controlled — change the Vercel value + redeploy, no code edit. The apply-page handoff still derives origin from `NEXT_PUBLIC_VELOXAHIRE_URL` and appends `/register?h=<token>` (token must stay in code). Updated §7 rule + `.env.example`/`.env.local`. Supersedes the origin-in-env rule from .6. | Claude (Evans) |
| 2026-06-21 | 2026-06-21.6 | Fixed cross-site nav double-pathing. Prod env vars carried a path (`NEXT_PUBLIC_VELOXAHIRE_URL=…/jobs`, `NEXT_PUBLIC_VELOXARECRUIT_URL=…/register`) and the code appended another → `/jobs/jobs` and `/register/get-started`. Now all link builders use `new URL(x).origin` then append one path: [ATS] `LandingPageClient.tsx` (`/jobs`) + `apply/[jobId]/page.tsx` (handoff `/register?h=`, `/jobs`); [HIRE] `app/page.tsx` (recruiter CTA now `/register`, was `/get-started`). Added the **origin-only env rule** to §7. Path-safe regardless of env, but keep env values as bare origins. | Claude (Evans) |
| 2026-06-21 | 2026-06-21.5 | Closed three audit code items. (1) **Narrowed the public apply response** — `PublicJobApplication` now `{application_id, received, handoff_token}` only; internal ids + pre_screen/decision/pipeline state no longer exposed to anonymous applicants (§5, gate #10 done). (2) [HIRE] **Restricted the Next image optimizer host** from `**.supabase.co` to the single project host (`frontend/next.config.js`) — closes the open image-proxy/cost vector. (3) Untracked build artifacts (`coverage.xml`, `*.tsbuildinfo`, `.ipynb_checkpoints/`) in both repos + added `.gitignore` rules. Verified: ATS handoff tests pass, narrowed model asserts only 3 fields. Remaining open: secret rotation + worker/beat/migrations (operational, owner), sync pagination cursor (§3, future). | Claude (Evans) |
| 2026-06-21 | 2026-06-21.4 | Added approved near-term front-door routing: VeloxaRecruit shows "I'm hiring" and "I'm looking for a job"; job seekers go to VeloxaHire `/jobs`; VeloxaHire shows "Create job for free" back to VeloxaRecruit request access. Auth remains separate; avoid one-login wording until the §6 broker exists. | Codex (Evans) |
| 2026-06-21 | 2026-06-21.3 | Corrected the identity contract after re-reading VeloxaRecruit auth code. Recruit auth must remain unchanged: it uses Supabase Auth via existing `SUPABASE_*` settings plus Recruit backend profile/status/email/rate-limit/session rules. Directly pointing VeloxaHire `supabase-js` at Recruit Supabase is not enough and can create orphaned users. Final one-login design must use a Recruit-owned auth broker/code exchange/provisioning flow while keeping databases separate. | Codex (Evans) |
| 2026-06-21 | 2026-06-21.2 | Updated identity contract from "SSO deferred" to auth-only unification: VeloxaRecruit Supabase Auth is canonical, VeloxaHire consumes that auth via `AUTH_SUPABASE_*` / `NEXT_PUBLIC_AUTH_SUPABASE_*`, and VeloxaHire data/storage stays on its own Supabase project. Added capability-model, callback URL, existing-user migration, and migration `012_drop_jobs_source_check.sql` notes. | Codex (Evans) |
| 2026-06-21 | 2026-06-21.1 | Created the shared ECOSYSTEM_CONTRACT.md (identical in both repos). Captures roles, current state (Phases 0–2 done, conversational WIP, SSO deferred), and the three contract surfaces: job sync (§3), handoff token (§4), apply loop (§5), shared secrets/migrations (§7). Records the audit-vs-code drift on handoff single-use (§9). Fulfills checklist task 3.1 "document the token contract." | Claude (Evans) |

---

## 11. Related docs (repo-specific detail — NOT synced)

**ATS (`AI-JOb-Assistant/`):**
- `docs/architecture/ECOSYSTEM_UNIFICATION_CHECKLIST.md` — executable build plan ("how")
- `docs/architecture/EMPLOYMENT_ECOSYSTEM_INTEGRATION_CHECKLIST.md` — architecture checklist
- `docs/architecture/ECOSYSTEM_UNIFICATION_AND_PRICING_PLAN_2026.md` — strategy ("why")
- `docs/architecture/VELOXA_ECOSYSTEM_OPERATIONS_GUIDE.md` — ops/env/verification
- `docs/memory/ecosystem_integration.md` — decision memory
- `docs/audits/ECOSYSTEM_UNIFICATION_DANGER_AUDIT_2026_06_21.md` — risk audit
- `docs/audits/CLAUDE_AUDIT_FACT_CHECK_2026_06_21.md` — audit fact-check

**VeloxaHire (`AI-Powered-JobHunt-Pro/`):**
- `MEMORY.md` §1–§7 — ecosystem context + sync/handoff detail
- `docs/deployment/DIGITALOCEAN_MIGRATION.md`, `docs/deployment/CELERY.md` — worker/beat ops
