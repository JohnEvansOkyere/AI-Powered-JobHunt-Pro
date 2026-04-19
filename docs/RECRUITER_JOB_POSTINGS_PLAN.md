# Recruiter Job Postings — Implementation Plan (Link-Out Apply)

Status: proposed
Owner: TBD
Target scope: MVP, candidates apply via an external URL the recruiter provides (no in-platform application, no CV review by recruiter).

## 1. Goal

Let verified recruiters post jobs on the platform. These jobs:

- Appear in the candidate search feed alongside scraped jobs.
- Are eligible for AI recommendations.
- Show an "Apply" button that opens the recruiter-provided URL in a new tab. That URL is the recruiter's own application page (their ATS, their careers site, a Google Form, etc.). The platform does not handle the application itself.

Out of scope for this plan:

- In-platform application submission.
- Recruiter-side candidate pipeline (review, status changes, messaging).
- Tailored-CV delivery to recruiters.
- Paid tiers / featured listings.

These are explicitly deferred to a future plan so this feature ships small.

## 2. Why link-out first

- Zero change to the candidate application model. `Application` behavior stays exactly as today for scraped jobs.
- No new PII flows (no CVs pushed to recruiters from the platform).
- Click-through is the only measurable outcome, which is enough to validate demand before investing in an ATS-style flow.
- Reuses existing `Job.job_link` semantics — recruiter jobs are "just another job source" from the candidate's perspective.

## 3. Concepts

| Concept | What it is |
|---|---|
| Role on a user | `candidate` (default), `recruiter`, `admin`. Controls which endpoints the user can call. |
| Organization | A company record. A recruiter posts on behalf of an organization, not as themselves. |
| Organization membership | Link between a user and an organization. One user can belong to multiple orgs. |
| Recruiter job | A `Job` row with `source='recruiter'`, an `organization_id`, a `posted_by_user_id`, and a `moderation_status`. |
| Apply URL | The external URL the recruiter wants candidates to visit to apply. Stored in the existing `Job.job_link` column. |

## 4. Data model changes

Single additive migration: `migrations/006_add_recruiter_jobs.sql`. Reconciled into `docs/SUPABASE_SETUP_COMPLETE.sql` in the same PR.

### 4.1 Users

Add a role column on `public.users`:

- `role` TEXT NOT NULL DEFAULT `'candidate'`, CHECK `role IN ('candidate', 'recruiter', 'admin')`.

Keep existing columns untouched. Backfill defaults to `'candidate'`.

### 4.2 Organizations

New table `public.organizations`:

- `id` UUID PK, default `uuid_generate_v4()`.
- `name` TEXT NOT NULL.
- `slug` TEXT UNIQUE NOT NULL (lowercase, URL-safe, derived from name).
- `website` TEXT NULL (must be https if present).
- `primary_domain` TEXT NULL (e.g., `acme.com`, used for email-domain auto-verification).
- `description` TEXT NULL.
- `logo_url` TEXT NULL.
- `verified` BOOLEAN NOT NULL DEFAULT FALSE.
- `verification_method` TEXT NULL, CHECK `verification_method IN ('email_domain_match', 'manual_admin', NULL)`.
- `created_by` UUID NOT NULL REFERENCES `public.users(id)`.
- `created_at`, `updated_at` TIMESTAMPTZ.

Indexes: `idx_orgs_slug`, `idx_orgs_primary_domain`.

### 4.3 Organization members

New table `public.organization_members`:

- `organization_id` UUID NOT NULL REFERENCES `organizations(id)` ON DELETE CASCADE.
- `user_id` UUID NOT NULL REFERENCES `users(id)` ON DELETE CASCADE.
- `role_in_org` TEXT NOT NULL, CHECK `role_in_org IN ('owner', 'member')`. Default `'member'`.
- `invited_by` UUID NULL REFERENCES `users(id)`.
- `accepted_at` TIMESTAMPTZ NULL.
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW().
- PRIMARY KEY `(organization_id, user_id)`.

For MVP there is no invite flow — the creator is auto-added as `owner`. The invite columns exist so adding invites later is additive.

### 4.4 Jobs

Additive columns on the existing `public.jobs` table:

- `organization_id` UUID NULL REFERENCES `organizations(id)` ON DELETE SET NULL.
- `posted_by_user_id` UUID NULL REFERENCES `users(id)` ON DELETE SET NULL.
- `moderation_status` TEXT NULL, CHECK `moderation_status IN ('pending', 'approved', 'rejected', 'closed', 'filled', 'expired')`. NULL for scraped/external jobs (not moderated).
- `moderation_reason` TEXT NULL.
- `expires_at` TIMESTAMPTZ NULL (separate from scraper cleanup; when past, job hides from feed).
- `apply_url_host` TEXT NULL (cached parsed hostname for display badges; optional).

Update the existing `source` CHECK to include `'recruiter'`. Existing sources stay as-is.

Semantics:

- For recruiter jobs, the external apply link is stored in the existing `Job.job_link` column. No new column is needed; we reuse the same field that scraped jobs use for "view on source".
- `processing_status` remains as-is (`pending`/`processed`/`archived` — about scraper processing). `moderation_status` is the new orthogonal axis for recruiter jobs.
- Old job-cleanup (>7 days) must skip recruiter jobs the same way it currently skips `external` jobs.

### 4.5 Migrations and seed

- `migrations/006_add_recruiter_jobs.sql` — all of the above.
- Update `docs/SUPABASE_SETUP_COMPLETE.sql` so a fresh database matches.
- Add RLS policies for `organizations` and `organization_members`:
  - A user can SELECT an organization they are a member of, or any `verified=true` organization.
  - A user can INSERT into `organizations` only if they have role in `('recruiter','admin')` in `public.users`.
  - Members can UPDATE their own org row if `role_in_org='owner'`.
- For the backend (which bypasses RLS), all of these must also be enforced in application code via dependencies. RLS is defense in depth only.

## 5. Moderation and trust

Spam is the #1 risk of letting users post jobs. Keep it simple for MVP:

1. User creates an organization. If the user's verified email domain matches `organizations.primary_domain`, set `verified=true` and `verification_method='email_domain_match'`.
2. Jobs posted under a verified organization by a verified-email user default to `moderation_status='approved'`.
3. Jobs posted under an unverified organization default to `moderation_status='pending'`.
4. Admin has a single moderation endpoint to approve or reject pending jobs.
5. Rate limit: max 20 job creations per organization per 24h, max 5 per hour per user.

No AI moderation in MVP. We're relying on (a) domain check, (b) rate limit, (c) admin review for the unverified tail.

## 6. Security requirements (non-negotiable)

These are the rules every change below must follow:

1. **Apply URL validation.** Even though the backend never fetches this URL, we still validate on create/update:
   - Scheme must be `https`. Reject `http`, `javascript:`, `data:`, `file:`, anything else.
   - Hostname must resolve publicly. Reject `localhost`, private IP ranges (10/8, 172.16/12, 192.168/16), link-local, multicast, `169.254.169.254`, `metadata.google.internal`.
   - Length ≤ 2048 chars.
   - Reuse the URL validator written for the SSRF fix in `external_job_parser.py`. Put the shared logic in `backend/app/utils/url_validator.py` so both call sites use it.
2. **Description sanitization.** Treat recruiter-submitted `description`, `requirements`, `responsibilities`, and `skills` as hostile text. Run through `utils/sanitizer.py` before persistence. Strip HTML to plain text (or an allowlist of `b`, `i`, `ul`, `ol`, `li`, `p`, `br` at most).
3. **No HTML injection in the frontend.** Never render recruiter-submitted text with `dangerouslySetInnerHTML`. This is already an open P1 audit finding for scraped descriptions; do not create a second instance of the same bug.
4. **Role and membership enforcement.** Two new FastAPI dependencies:
   - `require_role('recruiter', 'admin')` — fails 403 otherwise.
   - `require_org_membership(organization_id)` — fails 403 if current user is not a member of that org.
5. **Rate limiting.** Reuse whatever Redis-backed limiter is added for the `/jobs/scrape` P0 fix (see production audit). Apply to `POST /recruiter/jobs`.
6. **Outbound apply link anti-fraud.** On the frontend, the apply button uses `target="_blank" rel="noopener noreferrer nofollow"`. Optional: route through a platform redirect endpoint (see §7.5) so we can log clicks and kill a URL quickly if it turns malicious.
7. **Audit log.** Log every create/approve/reject/close action with `user_id`, `organization_id`, `job_id`, `request_id`, and timestamp. This is for abuse response, not analytics.

## 7. API design

All endpoints live under `backend/app/api/v1/endpoints/recruiter.py` and `admin.py` (both new files), wired into `api/v1/router.py`.

### 7.1 Self-service: become a recruiter

- `POST /api/v1/recruiter/enroll`
  - Input: nothing.
  - Effect: flips current user's `role` from `candidate` to `recruiter`. No-op if already recruiter/admin.
  - Returns: updated user.

### 7.2 Organizations

- `POST /api/v1/recruiter/organizations`
  - Input: `{ name, website?, primary_domain?, description?, logo_url? }`.
  - Creates org, adds caller as `owner`. Sets `verified=true` iff the caller's verified email domain matches `primary_domain`.
  - Requires role `recruiter` or `admin`.
- `GET /api/v1/recruiter/organizations/me` — orgs the caller belongs to.
- `GET /api/v1/recruiter/organizations/{org_id}` — must be a member.
- `PATCH /api/v1/recruiter/organizations/{org_id}` — must be `owner`.

### 7.3 Recruiter jobs

- `POST /api/v1/recruiter/jobs`
  - Input:
    - `organization_id` (required, caller must be a member).
    - `title` (required, ≤200 chars).
    - `description` (required, 200–10_000 chars after sanitization).
    - `apply_url` (required, https-only, validated).
    - `location` (optional).
    - `remote_type` enum (`remote`/`hybrid`/`onsite`, optional).
    - `job_type` enum (`full-time`/`part-time`/`contract`/`internship`, optional).
    - `experience_level` enum (optional).
    - `salary_min`, `salary_max`, `salary_currency` (optional, both min/max required together if present).
    - `skills` array of strings (optional, max 30).
    - `requirements`, `responsibilities` arrays of strings (optional).
    - `expires_at` timestamp (optional, default NOW() + 30 days, max NOW() + 90 days).
  - Creates a `Job` row with `source='recruiter'`, `organization_id`, `posted_by_user_id=current_user.id`, `job_link=apply_url`, `moderation_status` per §5, `scraped_at=NOW()`, `posted_date=NOW()`.
  - Requires role `recruiter` or `admin`, membership in the org, and passes rate limit.
- `PATCH /api/v1/recruiter/jobs/{job_id}` — caller must be a member of the job's org. Any edit drops `moderation_status` back to `pending` unless the job was already `approved` in a verified org.
- `POST /api/v1/recruiter/jobs/{job_id}/close` — sets `moderation_status='closed'`. No deletion.
- `GET /api/v1/recruiter/jobs` — list jobs for orgs I'm a member of, with filters `status`, `organization_id`.
- `GET /api/v1/recruiter/jobs/{job_id}` — detail, must be a member.

### 7.4 Admin moderation

- `GET /api/v1/admin/jobs?status=pending` — list jobs awaiting review.
- `POST /api/v1/admin/jobs/{job_id}/approve`.
- `POST /api/v1/admin/jobs/{job_id}/reject` — body `{ reason }`, stored in `moderation_reason`.

Requires `role='admin'`. No admin UI in MVP; admins can use the API docs.

### 7.5 Candidate-facing changes (minimal)

- `GET /api/v1/jobs/` — extend the existing filter so recruiter jobs are included by default when:
  - `source='recruiter'`
  - `moderation_status='approved'`
  - `expires_at IS NULL OR expires_at > NOW()`
  Scraped jobs continue to be included as today.
- `GET /api/v1/jobs/{job_id}` — unchanged, but the response already contains `job_link`, `source`, `source_url`. Frontend uses `source='recruiter'` to render the "Direct apply" badge.
- Optional: `GET /api/v1/jobs/{job_id}/apply` — a 302 redirect endpoint that (a) logs an apply-click event, (b) redirects to `Job.job_link`. Nice-to-have; can be added in a second PR without blocking MVP.

### 7.6 Response shape additions

Extend `JobResponse` (`backend/app/api/v1/endpoints/jobs.py`) with optional fields so the frontend can render badges without a second call:

- `organization_id: Optional[UUID]`
- `organization_name: Optional[str]` (joined in)
- `organization_logo_url: Optional[str]`
- `organization_verified: Optional[bool]`
- `moderation_status: Optional[str]`

None of these affect existing scraped-job responses (all NULL).

## 8. Recommendation behavior

No new AI work needed for MVP.

- `RecommendationGenerator` currently excludes `Job.source='external'` at `backend/app/services/recommendation_generator.py:111-116`. Leave that in place.
- Recruiter jobs (source='recruiter') flow through the matcher exactly like scraped jobs.
- Optional: add a small freshness + channel bonus in `AIJobMatcher` for recruiter jobs:
  - `+5` if `source='recruiter'`.
  - `+5` if `posted_date` within last 48h.
  These are real signals of active hiring; defer to a follow-up if we want to keep MVP minimal.
- `match_reason` for recruiter jobs should include "Posted by {org.name}" when an organization is joined in.

## 9. Frontend changes

All changes live under `frontend/`. No new libraries required.

### 9.1 Role gating

- Extend the current user profile shape (in `frontend/lib/auth.ts` or wherever the session is loaded) to include `role`.
- Add a `RecruiterRoute` wrapper (mirror of `ProtectedRoute`) that 302s to `/dashboard` if `role !== 'recruiter'` and `role !== 'admin'`.

### 9.2 Candidate-side

- `frontend/components/jobs/JobCard.tsx`:
  - If `job.source === 'recruiter'`, render a small "Direct apply" badge.
  - Apply button: for recruiter jobs, the button is a plain `<a>` with `href={job.job_link}`, `target="_blank"`, `rel="noopener noreferrer nofollow"`. (If §7.5 redirect endpoint is added, point to `/api/v1/jobs/{id}/apply` instead.)
- Job detail page (`frontend/app/dashboard/jobs/...`): same treatment, plus show org name, org logo, and "Posted on {date}" prominently.
- Never render the recruiter-submitted description with `dangerouslySetInnerHTML`. Use plain text or a sanitized Markdown renderer.

### 9.3 Recruiter-side

New folder `frontend/app/dashboard/recruiter/` with:

- `page.tsx` — "Become a recruiter" CTA if `role === 'candidate'` (calls `POST /recruiter/enroll`). Otherwise shows the recruiter dashboard.
- `organizations/page.tsx` — list my orgs and a "Create organization" form.
- `jobs/page.tsx` — list my jobs with status chips (pending/approved/rejected/closed/expired), "Post a new job" button.
- `jobs/new/page.tsx` — post-a-job form. All fields validated with `zod`:
  - URL field validates https only and hostname sanity in the browser (server re-validates).
  - Description is a textarea; show a character counter.
  - Show a preview of the candidate-facing job card.
- `jobs/[id]/page.tsx` — edit/close.

Corresponding API client in `frontend/lib/api/recruiter.ts`, with types aligned to the Pydantic response models.

### 9.4 Navigation

- Add a "Recruiter" entry in the dashboard sidebar that's only rendered when `role` is recruiter/admin.
- Keep the candidate-side nav unchanged for users who are not recruiters.

## 10. Click tracking (optional, recommended for Phase 1.5)

A tiny step that provides real value and is cheap:

- New table `job_apply_clicks(id, job_id, user_id, clicked_at, ip_hash, ua_hash)`. No raw IP, no raw UA — hash with a secret so it's useful for de-duplication but not identifying.
- New endpoint `GET /api/v1/jobs/{job_id}/apply` that inserts a row and issues a 302 to `Job.job_link`. Rate-limit and require auth.
- Aggregate per-job and per-org in the recruiter dashboard: "38 clicks in last 7 days".

This can be merged immediately after the base feature ships.

## 11. Phased task list

Each phase is a self-contained PR.

### Phase 1a — Schema and domain (1 day)

- [ ] Write `migrations/006_add_recruiter_jobs.sql`.
- [ ] Reconcile `docs/SUPABASE_SETUP_COMPLETE.sql`.
- [ ] Add SQLAlchemy models: `Organization`, `OrganizationMember`. Extend `User` with `role`, `Job` with the new columns.
- [ ] Unit tests: model create/read round-trip, constraints (invalid `source`, invalid `moderation_status`).

### Phase 1b — Backend endpoints (2 days)

- [ ] Implement `require_role` and `require_org_membership` dependencies in `backend/app/api/v1/dependencies.py`.
- [ ] Move / create shared `backend/app/utils/url_validator.py` (https-only, private-IP block, length cap). Use it from both recruiter jobs and the external-job parser SSRF fix.
- [ ] Implement `endpoints/recruiter.py` and `endpoints/admin.py`, wire into `api/v1/router.py`.
- [ ] Extend `endpoints/jobs.py` `JobResponse` and search filter to include recruiter jobs (`source='recruiter'` AND `moderation_status='approved'` AND not expired).
- [ ] Rate-limit `POST /recruiter/jobs` per user and per org.
- [ ] Audit log lines in a structured format for create/approve/reject/close.
- [ ] Negative authorization tests (cannot post to someone else's org, cannot edit another org's job, candidates cannot reach recruiter endpoints).

### Phase 1c — Frontend (2 days)

- [ ] Extend session/profile typing to carry `role`.
- [ ] New `RecruiterRoute` guard + sidebar entry.
- [ ] API client in `frontend/lib/api/recruiter.ts`.
- [ ] Recruiter dashboard pages (orgs, jobs list, new/edit, close).
- [ ] Candidate-side: recruiter badge on `JobCard` and detail page. External apply button with safe `rel` attributes.
- [ ] `npm run type-check` and `npm run build` pass.

### Phase 1d — Moderation and docs (0.5 day)

- [ ] Admin endpoints tested end-to-end.
- [ ] Update `docs/DEPLOYMENT.md` and `README.md` with the new feature.
- [ ] Add a short `docs/RECRUITER_POSTINGS.md` user guide for recruiters.
- [ ] Document the domain-match auto-verification rule and admin moderation workflow.

### Phase 2 (deferred, not in this plan)

- Click tracking (§10).
- Recommendation boost for recruiter/fresh jobs (§8).
- In-platform apply flow with CV + cover letter delivery.
- Recruiter-side candidate pipeline.
- Org invitations (multi-user organizations).

## 12. Testing plan

- Backend pytest:
  - Role transitions (candidate → recruiter via `enroll`).
  - Org creation (verified vs. unverified based on email domain).
  - Job create: valid, invalid URL scheme, private IP hostname, over-length description, missing required fields.
  - Moderation: domain-match auto-approve vs. pending.
  - Negative auth: candidate cannot post, recruiter cannot touch other orgs' jobs, admin can moderate.
  - Candidate `GET /jobs/` returns approved recruiter jobs, omits pending/rejected/closed/expired.
  - Rate limiting kicks in at the configured threshold.
- Frontend:
  - `type-check` and `build` pass.
  - Smoke test that the sidebar recruiter link is hidden for candidates and visible for recruiters.
  - Smoke test that the apply button for recruiter jobs uses `target="_blank" rel="noopener noreferrer nofollow"`.
- Migration:
  - Fresh database bootstraps from `docs/SUPABASE_SETUP_COMPLETE.sql` and from `migrations/` in sequence, and both end with the same schema.

## 13. Open questions

These need a product call before Phase 1a merges. Defaults are in parentheses.

1. Can recruiters self-enroll, or must admins grant the role? (Default: self-enroll.)
2. Is the `primary_domain` auto-verification enough for MVP, or do we require admin approval of every org? (Default: auto-verify on domain match, admin approval otherwise.)
3. Default job TTL: 30 days, capped at 90? (Default: yes.)
4. Should candidates see the recruiter's name (the user who posted), or only the organization? (Default: organization only, for privacy.)
5. Should recruiter jobs be pinned/boosted in recommendations? (Default: no boost in MVP; add a small freshness bonus in Phase 2.)

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Spam job postings flood the feed. | Rate limits + domain-match verification + admin moderation queue. |
| Malicious apply URLs (phishing, malware). | https-only + public-hostname check + `rel="noopener noreferrer nofollow"` + admin can flip `moderation_status='rejected'` instantly. |
| Recruiter puts PII or bad HTML in description. | Sanitizer pass on persistence; plain text rendering on the frontend. |
| Fresh-database schema drift (P2 audit item stays open). | Migration + complete setup SQL updated in the same PR; CI job runs both against a fresh DB (see production audit §15). |
| Scheduler duplicates work if we ever add recruiter-job cleanup. | Keep cleanup in Celery Beat per production audit §11, not in APScheduler. |

## 15. Alignment with existing audit

This plan is compatible with, and depends on, two in-flight fixes called out in `docs/PRODUCTION_SYSTEM_AUDIT_2026-04-18.md`:

- P0.1 (SSRF fix): the shared URL validator this plan introduces satisfies both the external-job parser fix and recruiter apply-URL validation.
- P1.5 (XSS via `dangerouslySetInnerHTML`): do not reintroduce it for recruiter descriptions. Plain text only.

If either of those fixes lands first, this feature inherits their guards. If this feature lands first, make sure the SSRF guard is at least in place at `utils/url_validator.py` before recruiter endpoints go live.
