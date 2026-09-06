# SEO and AI discovery

Implemented locally on 2026-09-06. Production deployment and search-provider verification remain separate steps. The original assessment is in `docs/audits/SEO_AI_DISCOVERY_AUDIT_2026_09_06.md`.

## Public routes and content

- `/` is a server page with explicit home metadata and the existing interactive design in `HomeClient.tsx`.
- `/jobs` fetches anonymous listings on the server. The first response includes job links; real Previous/Next links also work with JavaScript disabled. Search/filter/page state is encoded in the URL and survives back/forward navigation.
- Unfiltered pagination has self-canonical URLs. Arbitrary query/filter results, empty results and API failures have `noindex, follow`; campaign tags do not create canonical variants. Out-of-range pages return 404.
- `/ghana-jobs` lists complete jobs matched by the existing `location=Ghana` search, with original application guidance. City-only records may need a city search; this page does not claim complete Ghana coverage.
- `/remote-jobs` continues to render current listings on the server, omits known-closed/incomplete jobs and has a contextual footer link.
- `/about`, `/how-it-works`, `/job-sources`, `/contact` and `/guides/remote-jobs-from-ghana` explain the product, candidate choices, sources, limitations, data use and practical application checks. These are linked in the shared public footer and sitemap. Primary navigation remains concise.
- The support email is rendered only when `NEXT_PUBLIC_SUPPORT_EMAIL` contains a configured email address. **The owner must supply/confirm this public address.** No address, partnership, testimonial or comprehensive free-feature claim was invented. Candidate pricing/limits also need owner confirmation before publishing a pricing statement.

## Canonical host and crawler controls

`frontend/lib/site.ts` centralizes the canonical origin. Both known VeloxaHire hosts normalize to `https://www.veloxahire.org`, matching the redirect observed in the audit. Other configured origins, such as a local preview, retain their own origin.

- Set production `NEXT_PUBLIC_APP_URL=https://www.veloxahire.org` and retain the apex-to-www redirect at the host.
- Homepage, public catalogue, job details, legal pages and new public pages have appropriate canonical metadata.
- Root JSON-LD supplies basic Organization and WebSite identity. Job-detail Open Graph text now names VeloxaHire.
- `/robots.txt` allows public crawling and blocks `/api/`. It uses the same canonical origin for its sitemap/host declarations.
- `next.config.js` sends `X-Robots-Tag: noindex, nofollow` for `/auth/*`, `/dashboard/*`, `/profile/*` and `/register`. Those HTML routes are no longer blocked in robots, allowing compliant crawlers to see the noindex response. Authentication and ownership checks remain in place; this exposes no protected account data.
- No search-bot training permissions or infrastructure firewall settings were changed. No special AI file is required by this implementation.

## Job lifecycle and schema

`backend/app/services/public_jobs.py` defines shared active-job filters for general browse, local browse, the sitemap and public detail lookup:

1. The job is not archived.
2. Publication status is either absent (legacy/external records) or published.
3. A known application deadline is still in the future.

Closed/expired public detail requests return 404. The row is retained; candidate application history is not deleted. Active recruiter jobs are not closed merely because they are old. Existing cleanup and ATS lifecycle ownership are unchanged.

`JobResponse` now exposes the existing `application_deadline` column, which was introduced in migration `017_add_alx_job_imports.sql`. **No new migration is needed**, but the existing migration must already be applied before deploying this backend version.

The backend sitemap projects only IDs/update timestamps, checks nonblank content and an HTTP(S) application/source prefix, and excludes known-closed jobs. It caps at 49,000 jobs to leave room under the single-sitemap limit and logs `seo.sitemap.capacity_reached` at that cap. **Split into sitemap files before reaching that capacity.** The frontend additionally validates returned IDs/dates. Failed API requests log `seo.sitemap.fetch_failed`/`seo.sitemap.fetch_unavailable` while returning core pages; monitor these events for degraded job discovery. Core-page lastmod values are no longer fabricated from request time.

`frontend/lib/job-seo.ts` validates application URL protocols, known deadlines and complete visible content. It emits JobPosting only when the listing also supports usable geographic markup:

- Explicit recognized country names/codes are accepted; countries are not inferred from cities or AI-normalized fields.
- Onsite/hybrid locations include a country. Remote eligibility is emitted only for an unambiguous supported country label, optionally prefixed by `Remote,`.
- Worldwide, multi-country and ambiguous remote location labels currently omit JobPosting rather than guess. Those pages may still be indexed as ordinary HTML. Rich-result coverage can be expanded later with verified structured geography from sources.
- Employment types map to schema values. Known closing dates appear in both visible HTML and `validThrough`. No expiry date or salary is invented.
- Script delimiters are escaped before embedding untrusted strings in JSON-LD. Job descriptions remain rendered as text.

## Fetching and acquisition

Public catalogue requests have an eight-second timeout, per-render deduplication and explicit failure UI. They never forward a candidate token/cookie to the jobs API. Retry and edited search recovery are browser-tested. They do not cache candidate data.

The existing backend rate limits remain active: public search 60/minute, detail 120/minute and sitemap 10/minute per backend-visible client identity. **Verify real hosting proxy identity and SSR request volume during rollout:** server-originated requests can share an egress identity. Do not bypass rate limits or trust arbitrary forwarded headers to resolve that issue. No production load benchmark was performed.

Analytics now classifies recognizable ChatGPT, Perplexity, Claude, Gemini and Copilot referrers as `medium=ai`. Recognized source UTMs are normalized; explicit campaign medium/names are preserved. Existing admin acquisition reports consume these same stored source fields. Missing referrers remain unattributed/direct; a referral is not proof of an assistant endorsement. Historical events are not backfilled.

## Verification performed

- `cd frontend && npm run type-check` passed during implementation.
- An isolated `npm run build` passed with synthetic public API/Auth configuration. Existing Google Fonts fetching retried before succeeding.
- `cd backend && venv/bin/python -m pytest tests/test_public_job_discovery.py tests/test_production_hardening.py tests/test_ats_job_sync_service.py tests/test_user_privacy.py -q`: **33 passed**. Public-discovery tests use a real, isolated SQLite jobs table and do not access production data.
- `cd frontend && node scripts/verify-seo.cjs --unit`: **20 assertions passed**, covering canonical normalization, schema, missing/ambiguous geography, expiry, unsafe links, script escaping and query parsing.
- `scripts/verify-seo.cjs` against the isolated production server and synthetic local jobs API passed: all new public pages, self-canonicals, raw HTML links, JavaScript-disabled pagination, filters/back navigation, known-deadline schema, pending/noindex and closed/missing/invalid/overflow 404s, transactional noindex headers, robots/XML, API outage recovery and 360/390px layouts. No page JavaScript errors or candidate authorization headers on public server fetches were observed.
- Desktop About and mobile job-detail screenshots were inspected. Browser automation used installed Chrome through Playwright because `agent-browser` was unavailable.

## Production follow-up

1. Deploy the backend and frontend together, with the existing database migrations applied. No push/deployment was performed for this task.
2. Confirm the support email and candidate costs/limits; set the public contact configuration and rebuild.
3. Verify live apex/www behavior, robots, sitemap and sample job HTML. Monitor public API 429/503 responses and sitemap degradation logs.
4. Inspect an onsite role, eligible remote role and closed role in Google URL Inspection/Rich Results Test. Check canonical selection and job enhancement exclusions in Search Console. Submit only the XML sitemap URL as a sitemap. Verify Bing Webmaster Tools separately.
5. Monitor indexed eligible pages, useful search queries, AI referrals, application clicks and candidate activation. Measure real mobile performance/Core Web Vitals; synthetic browser success does not establish field performance.
6. Collect genuine permissioned candidate outcomes and third-party references. Add further location/entry-level pages only when inventory and original useful content support them. No outreach or publication to external services was performed.

Technical eligibility does not guarantee indexing, ranking or AI recommendations. Provider guidance: [Google AI features](https://developers.google.com/search/docs/appearance/ai-features), [Google JobPosting](https://developers.google.com/search/docs/appearance/structured-data/job-posting), [OpenAI crawlers](https://developers.openai.com/api/docs/bots).
