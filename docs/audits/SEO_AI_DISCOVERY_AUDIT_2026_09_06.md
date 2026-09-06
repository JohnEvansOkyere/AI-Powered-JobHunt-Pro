# VeloxaHire SEO and AI discovery audit — 2026-09-06

Follow-up implementation: technical repairs, public content and local verification are documented in `docs/features/SEO_AND_AI_DISCOVERY.md`. Findings below describe the pre-implementation assessment; production deployment/search-console verification remain outstanding.

## Assessment

VeloxaHire has a working search-discovery foundation, but is not yet well positioned to earn consistent recommendations from search engines or AI assistants. Public crawling is allowed and the live sitemap contains job URLs. Job index quality, crawlable navigation, clear product information, and evidence of usefulness need improvement.

“AI ready” here means discoverable and understandable by external AI search systems recommending tools or jobs to candidates. It is not an assessment of the reliability of the platform's internal matching or CV generation. Having internal AI features does not itself establish external recommendation visibility.

## Evidence and limits

### Verified live in this audit

- `https://veloxahire.org/` returned HTTP 308 to `https://www.veloxahire.org/`, then HTTP 200 HTML. The final page declares `https://veloxahire.org` as canonical, creating conflicting redirect/canonical signals.
- `/robots.txt` returned the public allow rule, private/transactional path disallows, and a sitemap declaration. There is no explicit public-site AI crawler block in that response.
- `/sitemap.xml` redirected to the www host and returned HTTP 200 `application/xml`. XML parsing found **87 URLs: 5 core pages and 82 job detail pages**. This resolves the previously documented core-pages-only sitemap observation. It does not establish that those 82 jobs are still open or indexed.
- The sitemap URLs use the non-www host, despite the www redirect destination.
- The fetched homepage HTML contains the product title, description and social metadata. Its HTML links include neither individual job detail URLs nor `/remote-jobs`.
- A search-tool query for `site:veloxahire.org jobs` returned no results. A brand search surfaced social mentions and another Veloxa product site. This is a limited discovery observation, **not proof of zero Google/Bing indexing or zero AI recommendations**.

### Verification gaps

- Follow-up raw HTML checks of `/jobs`, `/remote-jobs` and a sitemap job URL failed with DNS resolution timeouts, including retries outside the sandbox. This does not establish a production outage. Findings about those page implementations below come from source.
- No current Search Console/Bing Webmaster data, authenticated analytics, verified crawler logs, Rich Results Test, URL Inspection, Core Web Vitals or mobile browser measurements were available in this audit.
- No live expired-job sample was verified. The lifecycle inconsistency is confirmed in code; actual affected live rows remain unverified.
- No automated referral experiment across ChatGPT, Gemini or Perplexity was performed. Their recommendation frequency cannot be inferred from source.

## Confirmed source findings

| Priority | Finding | Evidence and consequence |
|---|---|---|
| P1 | Deadline handling is inconsistent | `backend/app/api/v1/endpoints/jobs.py`: `application_deadline` is checked only when the local scope is requested. General browse, `get_job_sitemap`, and `get_job` lack that check. `JobResponse` also omits the deadline. A processed job past its known deadline can remain eligible for public detail and sitemap output. |
| P1 | JobPosting markup is incomplete | `frontend/app/jobs/[id]/page.tsx`: `jobLocation.address` has only `addressLocality`, with no country; no `applicantLocationRequirements` or `validThrough` is emitted. `employmentType` passes raw internal values rather than mapping to supported values. `TELECOMMUTE` is inferred with a substring test. Validate against actual employer/source facts before emitting rich-result markup. |
| P1 | Main catalogue inventory depends on JavaScript | `frontend/app/jobs/page.tsx` wraps `JobsClient` in Suspense; `JobsClient.tsx` starts with an empty jobs array and fetches in `useEffect`. It provides no server-fetched initial inventory. Pagination uses state/buttons. Google may render JavaScript, but non-rendering crawlers cannot discover these listings from the initial catalogue response. Detail and remote pages do fetch on the server. |
| P1 | Public product and trust information is limited | There are no dedicated About, Contact, pricing/free-usage, matching explanation or career-resource routes. The homepage has three useful FAQs and explains CV tailoring, but does not fully answer ownership, service coverage, costs/limits, matching limitations, or support access. The privacy page refers to contact details elsewhere rather than providing an actual public contact address/link. |
| P2 | Remote landing page lost contextual incoming links | Current homepage, shared header and `JobsClient` do not link to `/remote-jobs`; it remains in the sitemap. Add a contextual/footer link without undoing the deliberately simplified primary navigation. |
| P2 | Canonical metadata leaks to pages without overrides | Root layout declares `/` as canonical. Privacy/terms provide titles and descriptions but no canonical overrides, so they inherit the homepage canonical. Auth/dashboard routes also have no explicit route-level noindex metadata in the inspected tree. Robots disallow does not itself remove indexed URLs; coordinate noindex with crawl access while preserving authentication. |
| P2 | Brand/schema consistency is incomplete | Site-level Organization/WebSite markup is absent; the Organization object present in job markup describes the hiring employer. Job-detail OG image alt text still names VeloxaRecruit. Add truthful site identity and distinguish candidate product, recruiter product, operator and employer. Schema is descriptive, not a recommendation guarantee. |
| P2 | Sitemap can silently degrade | The frontend returns core URLs on failed job fetches without surfacing an alert. Core page last-modified dates use request time, not actual edits. The backend caps at 50,000 jobs while the frontend adds 5 URLs; introduce sitemap splitting before that scale. Backend completeness checks are also weaker than the frontend's trimmed-text predicate. |
| P2 | Attribution exists but AI traffic is not grouped explicitly | `frontend/lib/analytics.ts` captures UTMs/referrers; backend `analytics.py` identifies organic/social traffic and preserves other hosts as referrals. AI hosts can already appear as generic referrals when a referrer is supplied. Add normalized AI-source reporting and candidate activation metrics; missing referrers remain unattributed. |

Existing lifecycle policy matters: `cleanup_old_jobs` deletes older scraped rows except records with applications, and exempts recruiter jobs whose lifecycle belongs to ATS publication status. Do not delete candidate history or impose age-based deletion on active recruiter roles to fix SEO. Known-closed jobs should leave the active search/schema path while protected history remains intact. Age alone is not evidence a job has closed.

## What to do, in order

### 1. Repair discovery and job eligibility

- Pick the preferred production host and align redirects, `NEXT_PUBLIC_APP_URL`, canonical metadata, sitemap entries and social URLs. Use the currently served www host unless intentionally changing the domain policy.
- Define a shared public/indexable-job rule that handles known deadlines, archival/publication state, complete content and usable application destinations. Preserve private history. For closed public pages, choose a clear closed/noindex page without active JobPosting markup or a proper 404/410 response as appropriate.
- Expose verified deadline and structured location/eligibility facts through backend response models and frontend types. Add accurate job markup; do not invent expiry dates, country eligibility or salary figures.
- Server-render an initial catalogue page with ordinary job links, and provide crawlable pagination with a deliberate query/filter canonical policy.
- Restore a contextual link to `/remote-jobs`, add correct legal-page canonicals, and coordinate transactional noindex rules with robots rules.
- Validate deployed examples: an onsite job, a geographically restricted remote job, a job with a deadline, an expired/archived job, an incomplete job, and a nonexistent job. Check status, HTML, canonical, schema, sitemap membership and application destination.

### 2. Make the platform easy to evaluate and cite

- Publish concise public answers: what VeloxaHire is, who operates it, whom it serves, where jobs come from, what browsing and account features cost, what account setup requires, and where applications go.
- Provide a real public support contact, source/freshness policy, scam-reporting route and plain-language CV/AI data-use explanation verified against actual behavior.
- Explain matching using a privacy-safe worked example: profile/CV inputs, relevance signals, what candidates should verify, and why recommendations do not guarantee interviews or hiring.
- Describe only shipped and live-verified capabilities. Internal documentation still lists deployment verification for tailored CVs and alerts; do not turn source-only status into public delivery claims.
- Add Organization/WebSite structured data referencing verified official profiles and operator identity. Keep employer identity separate in JobPosting markup.

### 3. Build useful search-intent content and independent evidence

- Start with a small number of pages supported by actual inventory: Ghana jobs, entry-level roles in Ghana, and remote roles whose stated eligibility includes Ghana. These are proposed topics, not verified keyword-demand findings.
- Give each page useful original guidance, current relevant job links, transparent eligibility and editorial ownership. Avoid making near-identical pages for every keyword/location combination.
- Publish candidate guides and product walkthroughs answering real questions, such as checking remote country restrictions and reviewing a tailored CV before applying.
- Collect permissioned user stories with verifiable outcomes. Seek genuine references from career services, training communities, recruiters and employers that have used the product. An imported ALX digest alone does not establish an ALX partnership or endorsement.
- Keep the VeloxaHire name, domain, audience and operator consistent across official channels. Existing ecosystem/social mentions are a starting point, not evidence of broad independent authority.

### 4. Measure discovery through candidate outcomes

- Inspect the correct domain property and sitemap in Google Search Console and Bing Webmaster Tools; inspect public HTML URLs, not backend JSON endpoints.
- Track indexed eligible jobs, indexing exclusions, job rich-result errors, relevant search impressions/clicks and available search AI reporting.
- Group recognizable AI referrers/UTMs, then follow landing → job view → apply click or signup → verified account → completed profile/CV → useful match engagement. Avoid logging CV contents or other private profile text.
- Maintain a small repeatable set of real job-seeker prompts and record date, assistant, exact question, cited URL and factual accuracy. Treat this as a sample, not a deterministic ranking score.
- Measure mobile performance and real candidate completion before claiming end-to-end readiness.

## AI-specific guidance

Public allow rules are already present; adding bot names alone is not the primary missing work. Verify production hosting/firewall access for legitimate search crawlers using provider guidance and logs. A spoofed user-agent check alone cannot prove IP-based crawler access.

OpenAI separates OAI-SearchBot (search discovery) from GPTBot (potential training use); training permission is not required for search visibility. User-initiated fetching is a separate mechanism. [OpenAI crawler documentation](https://developers.openai.com/api/docs/bots)

Google describes normal SEO, crawl access, textual content, internal linking and matching structured data as the foundation for its AI search features. It does not require an `llms.txt` file or special AI schema, and eligibility does not guarantee appearance. Treat `llms.txt` as optional documentation, not a launch blocker or visibility promise. [Google AI features guidance](https://developers.google.com/search/docs/appearance/ai-features)

Google requires country information when jobLocation is used, geographic eligibility for applicable remote jobs, and validThrough for known expiration dates. Expired listings need appropriate removal/closure handling. [Google JobPosting requirements](https://developers.google.com/search/docs/appearance/structured-data/job-posting)

## Work performed

Read-only source audit, public HTTP/header/XML inspection, and current primary-source guidance review. Added this report and updated the repo change log/open items. No application behavior, database, crawler permissions, deployment or external account settings changed. Application tests were not run because this task changes documentation only.
