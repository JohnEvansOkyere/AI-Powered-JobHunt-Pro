# Phase 6: Job Scraping System - Documentation

## Overview

Phase 6 implements a comprehensive job scraping system that collects job listings from multiple sources, normalizes the data, and stores it in the database. The system supports both traditional web scraping and AI-assisted extraction, with background processing via Celery.

## Architecture

### Components

1. **Scrapers** (`backend/app/scrapers/`)
   - Base scraper interface (`base.py`)
   - LinkedIn scraper (`linkedin_scraper.py`)
   - Indeed scraper (`indeed_scraper.py`)
   - AI-assisted scraper (`ai_scraper.py`)

2. **Services** (`backend/app/services/`)
   - Job Scraper Service (`job_scraper_service.py`)
   - Job Processor (`job_processor.py`)

3. **Background Tasks** (`backend/app/tasks/`)
   - Celery task for job scraping (`job_scraping.py`)

4. **API Endpoints** (`backend/app/api/v1/endpoints/`)
   - Job search and filtering (`jobs.py`)
   - Scraping job management

5. **Frontend** (`frontend/`)
   - Job search page (`app/dashboard/jobs/page.tsx`)
   - Job API client (`lib/api/jobs.ts`)

## Features Implemented

### New Source: SerpAPI (Google Jobs)
- Env: `SERPAPI_API_KEY=your_key`
- Source name: `serpapi`
- Example scrape request:
  ```json
  {
    "sources": ["serpapi"],
    "keywords": ["data scientist"],
    "location": "Ghana",
    "max_results_per_source": 30
  }
  ```
- Output is stored in `jobs` and then used by the matcher (profile + CV).

### 1. Multi-Source Job Scraping

- **Base Scraper Interface**: Common interface for all scrapers
- **LinkedIn Scraper**: Placeholder for LinkedIn integration
- **Indeed Scraper**: Placeholder for Indeed integration
- **AI Scraper**: Uses LLMs to extract job data from unstructured text

### 2. Job Data Normalization

- **Title Normalization**: Removes location suffixes, remote tags
- **Location Normalization**: Standardizes location formats
- **Salary Extraction**: Extracts salary ranges from descriptions
- **Job Type Extraction**: Identifies full-time, contract, etc.
- **Remote Type Extraction**: Identifies remote, hybrid, onsite

### 3. Job Deduplication

- **Link-based Deduplication**: Checks for duplicate `job_link`
- **Fuzzy Matching**: Matches by title + company + location within 30 days
- **Prevents Duplicate Storage**: Skips duplicates during scraping

### 4. Background Processing

- **Celery Integration**: Asynchronous job scraping tasks
- **Progress Tracking**: Tracks scraping progress via `scraping_jobs` table
- **Error Handling**: Retries failed scraping tasks
- **Batch Processing**: Processes multiple sources in parallel

### 5. Job Search & Filtering

- **Text Search**: Search by title, company, description
- **Source Filter**: Filter by job board source
- **Location Filter**: Filter by location
- **Job Type Filter**: Filter by full-time, contract, etc.
- **Remote Type Filter**: Filter by remote, hybrid, onsite
- **Date Filter**: Filter by posting date
- **Pagination**: Supports paginated results

### 6. Job Processing

- **AI Enrichment**: Uses AI to extract additional structured data
- **Batch Processing**: Processes pending jobs in batches
- **Status Tracking**: Tracks processing status (pending, processed, archived)

## Database Schema

### Jobs Table

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    description TEXT NOT NULL,
    job_link TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    source_id TEXT,
    posted_date TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    normalized_title TEXT,
    normalized_location TEXT,
    salary_range TEXT,
    job_type TEXT,
    remote_type TEXT,
    processing_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Scraping Jobs Table

```sql
CREATE TABLE scraping_jobs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    sources TEXT[] NOT NULL,
    keywords TEXT[],
    filters JSONB,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    jobs_found INTEGER DEFAULT 0,
    jobs_processed INTEGER DEFAULT 0,
    error_message TEXT,
    result_summary JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## API Endpoints

### Job Search

```
GET /api/v1/jobs/
Query Parameters:
  - q: Search query
  - source: Filter by source
  - location: Filter by location
  - job_type: Filter by job type
  - remote_type: Filter by remote type
  - min_posted_days: Minimum days since posted
  - page: Page number
  - page_size: Items per page
```

### Get Job

```
GET /api/v1/jobs/{job_id}
```

### Start Scraping

```
POST /api/v1/jobs/scrape
Body:
{
  "sources": ["linkedin", "indeed"],
  "keywords": ["software engineer"],
  "location": "San Francisco",
  "max_results_per_source": 50
}
```

### Get Scraping Job Status

```
GET /api/v1/jobs/scraping/{scraping_job_id}
```

### List Scraping Jobs

```
GET /api/v1/jobs/scraping/?status_filter=pending
```

## Usage Examples

### Starting a Scraping Job

```python
from app.services.job_scraper_service import JobScraperService
from app.core.database import SessionLocal

db = SessionLocal()
scraper_service = JobScraperService()

result = await scraper_service.scrape_jobs(
    sources=["linkedin", "indeed"],
    keywords=["software engineer", "python"],
    location="San Francisco",
    max_results_per_source=50,
    db=db
)
```

### Processing Pending Jobs

```python
from app.services.job_processor import JobProcessor
from app.core.database import SessionLocal

db = SessionLocal()
processor = JobProcessor()

processed_count = await processor.process_pending_jobs(db, limit=50)
```

### Searching Jobs via API

```typescript
import { searchJobs } from '@/lib/api/jobs'

const results = await searchJobs({
  q: 'software engineer',
  location: 'San Francisco',
  remote_type: 'remote',
  page: 1,
  page_size: 20
})
```

## Implementation Notes

### Scraper Placeholders

The LinkedIn and Indeed scrapers are currently placeholders. To implement full scraping:

1. **LinkedIn**:
   - Use LinkedIn's official API (requires partnership)
   - Or implement web scraping with proper rate limiting
   - Handle authentication and session management

2. **Indeed**:
   - Use Indeed's API if available
   - Or implement web scraping with pagination
   - Respect robots.txt and rate limits

### AI Scraper

The AI scraper can be used to:
- Extract job data from unstructured HTML/text
- Normalize job descriptions
- Extract structured information (skills, experience level, etc.)

### Rate Limiting

When implementing actual scrapers:
- Respect robots.txt
- Implement rate limiting (requests per minute)
- Use delays between requests
- Handle CAPTCHAs if encountered

### Error Handling

- Scraping tasks retry up to 3 times
- Failed jobs are logged with error messages
- Scraping job status is tracked in database

## Testing

### Manual Testing

1. **Start Scraping Job**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/jobs/scrape \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "sources": ["linkedin"],
       "keywords": ["software engineer"],
       "max_results_per_source": 10
     }'
   ```

2. **Search Jobs**:
   ```bash
   curl http://localhost:8000/api/v1/jobs/?q=engineer&page=1&page_size=20 \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Check Scraping Status**:
   ```bash
   curl http://localhost:8000/api/v1/jobs/scraping/SCRAPING_JOB_ID \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

## Future Enhancements

1. **Additional Job Boards**: Add more scrapers (Glassdoor, Monster, etc.)
2. **Real-time Scraping**: Implement continuous scraping with scheduling
3. **Job Matching**: Integrate with Phase 7 AI job matching
4. **Email Notifications**: Notify users of new matching jobs
5. **Job Alerts**: Allow users to set up job alerts
6. **Scraping Analytics**: Track scraping success rates, sources, etc.

## Troubleshooting

### No Jobs Found

- Check if scrapers are properly implemented
- Verify database connection
- Check scraping job status for errors

### Scraping Fails

- Check Celery worker is running
- Verify API keys for AI providers
- Check database connection
- Review error messages in `scraping_jobs` table

### Duplicate Jobs

- Deduplication logic checks `job_link` first
- Fuzzy matching may miss some duplicates
- Adjust deduplication logic if needed

## Dependencies

- `celery`: Background task processing
- `sqlalchemy`: Database ORM
- AI providers (OpenAI, Gemini, etc.) for AI scraper

## Files Created/Modified

### Backend

- `backend/app/scrapers/base.py` - Base scraper interface
- `backend/app/scrapers/linkedin_scraper.py` - LinkedIn scraper
- `backend/app/scrapers/indeed_scraper.py` - Indeed scraper
- `backend/app/scrapers/ai_scraper.py` - AI-assisted scraper
- `backend/app/services/job_scraper_service.py` - Scraping orchestration
- `backend/app/services/job_processor.py` - Job processing and enrichment
- `backend/app/tasks/job_scraping.py` - Celery task implementation
- `backend/app/api/v1/endpoints/jobs.py` - Job API endpoints

### Frontend

- `frontend/lib/api/jobs.ts` - Job API client
- `frontend/app/dashboard/jobs/page.tsx` - Updated to use real API

## Next Steps

Phase 6 is complete. The next phase (Phase 7) will implement AI-powered job matching, which will use the scraped jobs and user profiles to generate match scores and recommendations.

