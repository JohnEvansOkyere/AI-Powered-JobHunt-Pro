# Job Scraping Guide

## Current Sources
- **Remotive** (public API, no key needed)  
  - Endpoint: `https://remotive.io/api/remote-jobs`
  - Already integrated via `RemotiveScraper`
  - Best for remote-friendly roles across many categories

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

