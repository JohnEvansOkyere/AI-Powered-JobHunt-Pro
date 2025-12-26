# Automated Job Scraping

This document explains how the automated job scraping system works and how to set it up.

## Overview

The platform automatically scrapes fresh tech jobs **every 3 days** from multiple FREE sources to keep the job database up-to-date without manual intervention.

## Features

✅ **Fully Automated**: Runs on a schedule without manual intervention
✅ **100% Free**: Uses only free APIs (Remotive + RemoteOK) - no API keys needed
✅ **Tech-Focused**: Targets 20+ tech job categories
✅ **Scalable**: Uses Celery for distributed task processing
✅ **Fault-Tolerant**: Automatic retries and error handling
✅ **Tracked**: All scraping jobs are logged in the database

## Tech Job Categories

The scheduler automatically searches for these tech roles:

**Software Engineering:**
- Software Engineer
- Backend Engineer
- Frontend Engineer
- Full Stack Developer
- Mobile Developer
- DevOps Engineer

**Data & AI:**
- Data Scientist
- Data Analyst
- Machine Learning Engineer
- AI Engineer
- Data Engineer
- Business Intelligence Analyst

**Product & Design:**
- Product Manager
- UX Designer
- UI Designer
- Product Designer

**Other Tech Roles:**
- Cloud Engineer
- Security Engineer
- QA Engineer
- Site Reliability Engineer

## Architecture

```
┌─────────────────┐
│  Celery Beat    │  ← Scheduler (runs every 3 days)
│   (Scheduler)   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Celery Worker  │  ← Executes scraping tasks
│  (Task Runner)  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Job Scrapers   │  ← SerpAPI + Remotive
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  PostgreSQL DB  │  ← Stores scraped jobs
└─────────────────┘
```

## Setup Instructions

### Option 1: Using Docker Compose (Recommended)

This is the easiest way to run everything:

```bash
# Start Redis + Celery Worker + Celery Beat
docker-compose up -d

# View logs
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat

# Stop services
docker-compose down
```

### Option 2: Manual Setup

#### 1. Install Redis

```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# macOS
brew install redis
brew services start redis
```

#### 2. Install Celery

```bash
cd backend
pip install celery redis
```

#### 3. Start Services

**Terminal 1 - Celery Worker:**
```bash
cd backend
./start_celery_worker.sh
```

**Terminal 2 - Celery Beat (Scheduler):**
```bash
cd backend
./start_celery_beat.sh
```

**Terminal 3 - FastAPI Backend:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Schedule Configuration

The scraper runs **every 3 days at 2:00 AM UTC**.

To change the schedule, edit `backend/app/tasks/periodic_tasks.py`:

```python
# Current: Every 3 days at 2 AM
sender.add_periodic_task(
    crontab(hour=2, minute=0, day_of_week='*/3'),
    scheduled_tech_job_scraping.s(),
    name='scrape-tech-jobs-every-3-days'
)

# Example: Every day at midnight
sender.add_periodic_task(
    crontab(hour=0, minute=0),
    scheduled_tech_job_scraping.s(),
    name='scrape-tech-jobs-daily'
)

# Example: Every Monday at 9 AM
sender.add_periodic_task(
    crontab(hour=9, minute=0, day_of_week=1),
    scheduled_tech_job_scraping.s(),
    name='scrape-tech-jobs-weekly'
)
```

## Data Sources

### 1. Remotive (FREE)
- **API Key Required**: No (public API)
- **Coverage**: Remote jobs worldwide
- **Job Types**: Tech and non-tech
- **Rate Limit**: Reasonable use
- **Cost**: $0

### 2. RemoteOK (FREE)
- **API Key Required**: No (public API)
- **Coverage**: Remote jobs worldwide
- **Job Types**: All tech roles
- **Rate Limit**: Reasonable use
- **Cost**: $0

## Monitoring

### Check Scraping Status

```bash
# View recent scraping jobs
curl http://localhost:8000/api/v1/jobs/scraping/

# Check specific scraping job
curl http://localhost:8000/api/v1/jobs/scraping/{scraping_job_id}
```

### Database Queries

```python
from app.core.database import SessionLocal
from app.models.scraping_job import ScrapingJob

db = SessionLocal()

# Get recent scraping jobs
recent_jobs = db.query(ScrapingJob).order_by(
    ScrapingJob.created_at.desc()
).limit(10).all()

for job in recent_jobs:
    print(f"Status: {job.status}")
    print(f"Found: {job.jobs_found} jobs")
    print(f"Stored: {job.jobs_processed} jobs")
    print(f"Result: {job.result_summary}")
```

### Celery Monitoring (Flower)

Install Flower for a web-based monitoring UI:

```bash
pip install flower
celery -A app.tasks.celery_app flower
```

Then open: http://localhost:5555

## Manual Trigger

To manually trigger a scraping job (for testing):

```python
from app.tasks.periodic_tasks import scheduled_tech_job_scraping

# Trigger immediately
result = scheduled_tech_job_scraping.delay()
print(f"Task ID: {result.id}")
```

Or via API:

```bash
curl -X POST http://localhost:8000/api/v1/jobs/scrape \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "sources": ["remotive", "remoteok"],
    "keywords": ["data scientist", "machine learning"],
    "location": "United States",
    "max_results_per_source": 200
  }'
```

## Customization

### Add More Keywords

Edit `backend/app/tasks/periodic_tasks.py`:

```python
TECH_JOB_KEYWORDS = [
    # Add your keywords here
    "blockchain developer",
    "web3 engineer",
    "smart contract developer",
]
```

### Add More Sources

Edit `backend/app/tasks/periodic_tasks.py`:

```python
# Current free sources:
sources=["remotive", "remoteok"]

# To add more sources (some may require API keys):
sources=["remotive", "remoteok", "indeed", "linkedin"]
```

### Change Results Per Source

Edit `backend/app/tasks/periodic_tasks.py`:

```python
# Change max_results_per_source
max_results_per_source=200  # Get more results
```

## Troubleshooting

### Celery Worker Not Starting

```bash
# Check Redis connection
redis-cli ping  # Should return "PONG"

# Check Celery configuration
celery -A app.tasks.celery_app inspect active
```

### No Jobs Being Scraped

1. Check if Beat is running: `ps aux | grep celery`
2. Check Beat logs for schedule execution
3. Verify Redis is running: `systemctl status redis`
4. Check worker logs: `celery -A app.tasks.celery_app events`

### Scraper Connection Errors

- Verify network connectivity to Remotive and RemoteOK APIs
- Check if the APIs are responding: `curl https://remotive.com/api/remote-jobs`
- Check if RemoteOK API is responding: `curl https://remoteok.com/api`
- Review error messages in worker logs

## Production Deployment

### Using Supervisor (Recommended)

Create `/etc/supervisor/conf.d/celery.conf`:

```ini
[program:celery_worker]
command=/path/to/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info
directory=/path/to/backend
user=your_user
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

[program:celery_beat]
command=/path/to/venv/bin/celery -A app.tasks.celery_app beat --loglevel=info
directory=/path/to/backend
user=your_user
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

Then:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery_worker celery_beat
```

### Using Systemd

Create service files in `/etc/systemd/system/`.

## Performance

- **Jobs per scrape**: ~400-600 depending on keywords and availability
- **Execution time**: 3-10 minutes per run
- **Deduplication**: Automatic (by job URL and title+company)
- **Storage**: ~1KB per job (text content)

## Cost Estimation

- **Redis**: Free (self-hosted) or ~$5-10/month (managed)
- **Remotive API**: Free (public API) - $0
- **RemoteOK API**: Free (public API) - $0
- **Server**: Minimal overhead (can run on existing backend server)
- **Total API Costs**: $0/month

## Next Steps

1. Start the services using Docker Compose or manually
2. Wait for the first scheduled run (or trigger manually)
3. Monitor the scraping jobs via API or database
4. Customize keywords and schedule as needed
5. Set up monitoring/alerting for production
