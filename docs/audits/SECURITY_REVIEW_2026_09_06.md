# Security review — 2026-09-06

## Assessment and scope

The highest-priority findings are self-service administrator escalation, a public CV bucket, and backend storage operations that trust user-writable file paths. These need remediation before treating candidate data as adequately protected.

Evidence comes from the current working-tree source, read-only inspection of the database configured by `backend/.env`, a zero-row Supabase Data API request, locally installed package metadata, maintainer advisories, and synthetic function checks. Concurrent admin/SEO changes were present and were not modified by this review. The configured Auth and data projects match. This does not independently establish which commit/environment the deployed frontend/backend use.

No account permissions were changed, no CV objects were read or deleted, no SMS or AI requests were sent, and no denial-of-service payloads were executed. There is no conclusion about past exploitation; access logs and incident evidence were not reviewed.

## Prioritized findings

### S1 — Critical: users can change their own administrator and suspension flags

**Confirmed configured-database permissions and source; no live privilege escalation performed.**

- `public.users` has RLS enabled, but its UPDATE policy only requires `auth.uid() = id`. The authenticated role has UPDATE permission on `is_admin`, `is_active`, email and phone fields. The only non-internal account trigger updates `updated_at`; it does not protect those fields.
- A zero-row request to the configured `/rest/v1/users` using its public API key returned HTTP 200 with `[]`, confirming the table is exposed through the Data API without retrieving account data.
- [Admin authorization](../../backend/app/api/v1/dependencies.py) trusts `public.users.is_admin`. The checked policy permits an authenticated user to promote their own account; backend admin access additionally requires the existing valid/phone-verified account checks. A suspended user retaining an Auth session can also change the local active flag.
- The [complete setup script](../SUPABASE_SETUP_COMPLETE.sql), lines 774–777, reproduces this unrestricted own-row update policy. Migration `015` adds the admin flag without restricting its writes.

**Impact:** unauthorized administrative access, account-data exposure, suspension bypass, and use of account suspension/deletion functions. UI hiding does not protect this path.

**Fix:** revoke direct account-table writes from browser roles and expose an explicitly limited profile-update operation, or revoke table-level UPDATE and grant only safe columns. Keep role, active status and canonical identity server-controlled. Check INSERT permissions/policies too; audit other trusted fields in user-writable tables. Add real database-role tests proving ordinary users cannot change administrative fields. RLS limits rows; column privileges must separately limit fields. [Supabase column security](https://supabase.com/docs/guides/database/postgres/column-level-security).

### S2 — High: uploaded CV storage is public

**Confirmed configured storage metadata.**

The configured CV bucket has `public=true`, `file_size_limit=NULL`, and `allowed_mime_types=NULL`. Its policies restrict owner uploads/updates/deletes, but a public bucket bypasses download access control. A person who obtains an object's path can retrieve it without signing in; UUID paths do not make documents private. The backend's one-hour signed URL does not remove the separate public-download route. This does not prove that all object paths are enumerable. [Supabase bucket access semantics](https://supabase.com/docs/guides/storage/buckets/fundamentals).

**Impact:** CV names, contact details and career history can be exposed through leaked/shared object URLs. The storage INSERT policy also permits authenticated users to upload directly to their own folder, bypassing FastAPI's upload validation; no bucket-specific size/type restrictions were configured.

**Fix:** make the CV bucket private, verify owner-scoped downloads and anonymous denials, add bucket size/type restrictions, and review any historical public URL distribution and access evidence. Changing visibility cannot recall documents already downloaded. The setup script currently asks the operator to create the bucket manually and does not enforce private visibility.

### S3 — High: user-writable CV paths reach service-role signing and deletion

**Confirmed database permissions, source, and synthetic execution.**

- The authenticated role can update `public.cvs.file_path`. Its RLS policy checks ownership of the database row, without binding the stored path to that owner.
- [CV download and deletion](../../backend/app/api/v1/endpoints/cvs.py), lines 408–411 and 435–450, check row ownership, then use the backend service role on `cv.file_path` without checking the storage folder owner.
- A synthetic owned CV row pointing to another synthetic user's folder was accepted by both the real signing and deletion functions using mocked storage. No real storage operations occurred.

**Impact:** a user who knows another object's path could make the backend sign or delete that object by changing their own CV row. This remains a problem after the bucket is made private.

**Fix:** prohibit client changes to storage paths and parser-controlled fields; bind or derive each file path from its trusted owner/record ID; enforce that invariant before every privileged storage operation. Test cross-owner paths, malformed paths and forged metadata. Audit account-deletion storage cleanup for the same invariant.

### S4 — High: upload dependencies have published denial-of-service vulnerabilities

**Confirmed local packages and requirements; deployed package versions unverified.**

Both requirements files pin FastAPI `0.104.1` and `python-multipart==0.0.6`; the local environment has those versions and Starlette `0.27.0`. The multipart maintainer identifies `<=0.0.6` as vulnerable to crafted Content-Type headers consuming CPU and blocking request processing. A separate multipart boundary advisory affects old releases as well. File uploads make multipart parsing relevant; no attack was executed. [Header advisory](https://github.com/Kludex/python-multipart/security/advisories/GHSA-2jv5-9r88-3w3p), [boundary advisory](https://github.com/Kludex/python-multipart/security/advisories/GHSA-59g5-xgcq-4qw3).

**Fix:** upgrade FastAPI, Starlette and multipart together to compatible versions checked against current advisories, lock the resolved production dependencies, and exercise authentication and file-upload regressions. Do not assume the first historically patched release covers subsequent advisories. This was not a comprehensive Python/npm dependency audit.

### S5 — High: expensive CV and legacy matching paths lack adequate abuse controls

**Confirmed source; no load test or provider billing test.**

- `POST /api/v1/cvs/upload` has no per-user upload quota/rate limiter. It reads the file and parses PDF/DOCX within the request. Parsing loops over all pages/paragraphs without page, expanded ZIP size, extraction-time or extracted-text memory limits. The 10 MB compressed input limit does not bound document expansion or processing work.
- CV parsing calls the AI router without `user_id`; its optional user-based rate check therefore does not run for that call. Repeated uploads also retain inactive CV records/files.
- `POST /api/v1/jobs/recommendations/generate` delegates directly to V2 matching without the rate guard used by the newer regeneration route, providing an alternative expensive entry point.

**Impact:** elevated AI/storage bills, worker/database pressure and application unavailability. [OWASP resource-consumption guidance](https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/).

**Fix:** shared user/global quotas, concurrency and daily spending caps, consistent guards on every entry point, bounded asynchronous document workers, ZIP/page/text limits, idempotency, and storage retention limits. Keep direct Supabase writes from bypassing these controls.

### S6 — Medium: shared IP rate limits trust untrusted forwarded headers

**Confirmed source and synthetic check; actual proxy sanitation unverified.**

[The shared limiter](../../backend/app/core/rate_limit.py), lines 30–35, uses the first `X-Forwarded-For` value before the ASGI peer. A synthetic request confirmed this behavior. The documented Nginx configuration appends through `$proxy_add_x_forwarded_for`, preserving a supplied first value. If deployed that way, callers can vary that value to evade public endpoint limits.

**Fix:** configure trusted proxy handling and use the verified peer identity, or have the trusted edge overwrite the header correctly. Test the deployed chain. User-ID-based limits are not affected by this header issue. SMS password recovery has a separate helper that already uses the ASGI peer.

### S7 — Medium: CV-derived AI output can enter ordinary logs

**Confirmed source; no production log contents inspected.**

[CV parsing](../../backend/app/services/cv_parser.py), line 198, logs the first 500 characters of an invalid AI JSON response. That response may include names, phone numbers or other resume content. The logging pipeline has no general personal-data scrubber, and this is an error-level log even with DEBUG disabled.

**Fix:** remove raw AI/CV content from diagnostic logs; retain error categories, request IDs, sizes and non-sensitive status. Review log access/retention and historical exposure before concluding whether data leaked.

## Additional risks requiring targeted verification

- **SSRF/DNS rebinding:** `external_job_parser.py` validates DNS answers, then HTTPX separately resolves/connects to the hostname. Connections are not pinned to the validated address. Private-IP rejection, redirect checks, HTTPS restrictions and response caps exist, but the validation/connection race remains a source-level concern. TLS and deployed egress controls affect exploitability. Verify using a controlled environment and enforce public-only egress or a safe pinned resolver. No internal network probes were made. [OWASP SSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
- **Redis exposure:** `docker-compose.yml` publishes Redis on `6379:6379` with no password/ACL in that file. If used on a reachable interface without firewall protection, queue/rate-limit/recovery state can be tampered with. Other deployment docs use localhost Redis, so internet exposure is not established. Check the actual binding/firewall, use private networking and appropriate authentication. Celery accepts JSON; arbitrary-code execution from pickle is not asserted.
- **AI instruction manipulation:** initial CV parsing concatenates untrusted CV text into its prompt and persists `json.loads` output without a schema check. The later tailoring flow has stronger bounded validation. An injected document can corrupt parsed facts or downstream matching. This review did not establish tool execution, secret access or cross-account AI data access. Treat prompts as untrusted input, validate output shape and preserve human review.
- **Admin account takeover:** admin authorization does not require MFA assurance or recent reauthentication for destructive operations. SMS verification at signup does not provide a second factor for every admin login. Add stronger operator authentication and auditable privileged actions after fixing S1.

## Existing protections observed

Backend dependencies verify Auth identity, reject missing/suspended local accounts, and check authoritative phone confirmation. Most reviewed CV/profile/application/generated-CV handlers scope records to the current user. Password recovery uses canonical Auth identity checks, bounded codes, atomic Redis grants, replay controls and no-store responses. Public job descriptions render as text; JSON-LD is escaped. These controls are useful, but direct Data API permissions and privileged storage paths can bypass some intended boundaries.

## Verification record and limits

| Check | Result |
|---|---|
| Configured database metadata, read-only transaction | Account admin/active columns and CV path are writable by authenticated role; own-row policies confirmed; no protecting account trigger |
| Configured CV bucket metadata | Public; no bucket-specific file size/type restriction |
| Data API request with `select=id&limit=0` | HTTP 200, empty array, no account records retrieved |
| Synthetic CV signing/deletion | Both accepted an owned row containing an outside-owner storage path |
| Synthetic forwarded-header identity | Caller-supplied first forwarded value overrides peer |
| Installed versions and official advisories | Outdated multipart version confirmed; production versions not inspected |

No production exploit, authenticated cross-account HTTP test, complete dependency/secret-history scan, firewall inspection, provider-retention review or incident investigation was performed. Follow-up authorization tests should use isolated representative accounts/data. Broad existing API tests were not run because this task changed documentation only and some existing tests access the configured database.

## Remediation order

1. Close direct administrative writes, make CV storage private, and enforce owner-bound storage paths together.
2. Upgrade the upload stack and close upload/matching resource-abuse paths.
3. Correct trusted-proxy rate limiting and remove sensitive diagnostic content.
4. Verify egress/Redis exposure and add admin MFA, database-policy regressions, dependency scanning and incident/audit coverage.

Runtime code, live permissions, account data and deployments remain unchanged by this assessment.
