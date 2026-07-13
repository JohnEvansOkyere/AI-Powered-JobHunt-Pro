# Job Scraping Guide

## Current Sources

Free, no API key (all on the Celery Beat scheduled scrape as of 2026-07-13):

| Source | Slug | Coverage | Endpoint |
|---|---|---|---|
| Remotive | `remotive` | Global remote, all categories | `https://remotive.com/api/remote-jobs` (`.io` is dead — Cloudflare 526) |
| RemoteOK | `remoteok` | Global remote, ~100 latest | `https://remoteok.com/api` |
| Arbeitnow | `arbeitnow` | Europe + remote | `https://www.arbeitnow.com/api/job-board-api` |
| Jobicy | `jobicy` | Global remote, tech + non-tech | `https://jobicy.com/api/v2/remote-jobs` |
| Himalayas | `himalayas` | Global remote | `https://himalayas.app/jobs/api` |
| The Muse | `themuse` | Global, strong non-tech (support, marketing, healthcare) | `https://www.themuse.com/api/public/jobs` |
| Working Nomads | `workingnomads` | Global remote, ~30 latest | `https://www.workingnomads.com/api/exposed_jobs/` |
| We Work Remotely | `weworkremotely` | Global remote (RSS) | `https://weworkremotely.com/remote-jobs.rss` |
| MyJobMag Ghana | `myjobmag` | Ghana, all role types (feed currently stale — auto-recovers) | `https://www.myjobmagghana.com/jobsxml.xml` |
| MyJobMag Nigeria | `myjobmag_ng` | Nigeria, all role types | `https://www.myjobmag.com/jobsxml.xml` |
| MyJobMag Kenya | `myjobmag_ke` | Kenya, all role types | `https://www.myjobmag.co.ke/jobsxml.xml` |
| MyJobMag South Africa | `myjobmag_za` | South Africa, all role types | `https://www.myjobmag.co.za/jobsxml.xml` |
| JobWeb Ghana | `jobwebghana` | Ghana (RSS, ~10 latest) | `https://jobwebghana.com/feed/` |

API-key sources (enabled when the key is set in `.env`): SerpAPI (`SERPAPI_API_KEY`), Jooble (`JOOBLE_API_KEY`), FindWork (`FINDWORK_API_KEY`), Adzuna (`ADZUNA_APP_ID`+`ADZUNA_APP_KEY`).

Removed: **Joinrise** (2026-07-13 — site and API down, 503). The scraper class remains registered and fails gracefully if the API returns.

Keywords: scheduled scraping uses `ALL_JOB_KEYWORDS` (`app/constants/`) = `TECH_JOB_KEYWORDS` + `GENERAL_JOB_KEYWORDS` (customer support, digital marketing, sales, finance, HR, healthcare, education, logistics, etc.). The ingest window is 7 days, matching the 7-day retention in `cleanup_old_jobs`.

## How to Run Scraping
- Celery task `scrape_jobs` accepts `sources`, `keywords`, `location`, `max_results_per_source`.
- If `sources` is empty, it defaults to `["remotive"]`.
- You can trigger via `/api/v1/jobs/scrape` with a POST body like:
```json
{
  "sources": ["remotive"],
  "keywords": ["python", "data"],
  "location": "remote",
  "max_results_per_source": 50
}
```

## Adding More Job Boards
1) **Public APIs (recommended)**
   - Find a job board with an open API (or RSS/JSON feed).
   - Create a new scraper in `backend/app/scrapers/<name>_scraper.py` that:
     - Fetches jobs from the API
     - Maps fields to `JobListing`
     - Normalizes title/location/remote_type and parses posted_date
   - Register it in `JobScraperService` (`self.scrapers` dict).

2) **RSS/Atom Feeds**
   - Many boards expose RSS feeds; use `feedparser` or `requests` to pull entries.
   - Map entry title/link/summary to `JobListing`.

3) **Official APIs (with keys)**
   - If you have keys (e.g., Greenhouse, Lever, Workable, SmartRecruiters):
     - Add env vars for API keys.
     - Implement a scraper using `requests` with proper headers/auth.
   - For LinkedIn: official API requires partnership; scraping LinkedIn pages directly is discouraged and may violate their ToS.

4) **HTML Scraping (last resort)**
   - Use only if allowed by the site’s ToS.
   - Respect robots.txt, add rate limiting/backoff.
   - Parse HTML with `BeautifulSoup`/`lxml`.
   - Rotate user agents, avoid excessive requests.

## Data Quality & Deduplication
- Deduplication is done on `job_link` and fuzzy title/company/location.
- Set `processing_status` to `processed` when normalized.

## Matching Workflow
1. Scrape jobs → stored in `jobs` table.
2. Matching uses:
   - CV parsed skills/experience (active CV)
   - Profile skills/experience/preferences
3. Frontend calls `/api/v1/jobs/?matched=true` to fetch matched jobs with scores.

## Common Pitfalls
- Empty jobs table: ensure scraper runs and commits.
- Missing `processing_status`: keep `processed` or `pending`, avoid `archived`.
- Timeouts: set reasonable limits; avoid large `max_results_per_source`.

## Next Steps
- Add another public source (e.g., Remotive categories, RemoteOK/others if ToS allows).
- Add scheduling (Celery beat) to refresh jobs periodically.

