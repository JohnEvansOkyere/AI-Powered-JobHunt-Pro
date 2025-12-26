# 🤖 Automated Job Scraping System

## Overview

This platform includes a **fully automated job scraping system** that runs on a schedule to keep your job database fresh with the latest tech opportunities.

## Key Features

✅ **Automated Scraping**: Runs every 3 days automatically
✅ **Multi-Source**: SerpAPI (Google Jobs) + Remotive  
✅ **Tech-Focused**: 20+ tech job categories  
✅ **Production-Ready**: Fault-tolerant with automatic retries  
✅ **Scalable**: Uses Celery for distributed processing  
✅ **Zero Maintenance**: Set it and forget it  

## Quick Start

```bash
# 1. Start Redis
redis-server

# 2. Start Celery Worker (Terminal 1)
cd backend
celery -A app.tasks.celery_app worker --loglevel=info

# 3. Start Celery Beat Scheduler (Terminal 2)
cd backend  
celery -A app.tasks.celery_app beat --loglevel=info
```

**That's it!** The system will now automatically scrape fresh tech jobs every 3 days.

## What Gets Scraped?

The scheduler automatically searches for:

- **Software Engineering**: Backend, Frontend, Full Stack, Mobile, DevOps
- **Data & AI**: Data Scientists, ML Engineers, Data Analysts, Data Engineers
- **Product & Design**: Product Managers, UX/UI Designers
- **Infrastructure**: Cloud, Security, QA, SRE

**Results**: ~200-500 new jobs every 3 days from worldwide sources.

## Architecture

```
Celery Beat (Scheduler)
    ↓ (every 3 days at 2 AM UTC)
Celery Worker (Task Processor)
    ↓ (scrapes from)
SerpAPI + Remotive
    ↓ (stores in)
PostgreSQL Database
```

## Configuration

### Change Schedule

Edit `backend/app/tasks/periodic_tasks.py`:

```python
# Every 3 days at 2 AM (default)
crontab(hour=2, minute=0, day_of_week='*/3')

# Daily at midnight
crontab(hour=0, minute=0)

# Every Monday at 9 AM
crontab(hour=9, minute=0, day_of_week=1)
```

### Add Job Keywords

Edit `backend/app/tasks/periodic_tasks.py`:

```python
TECH_JOB_KEYWORDS = [
    "software engineer",
    "data scientist",
    # Add more here...
]
```

### Change Sources

Edit `backend/app/tasks/periodic_tasks.py`:

```python
sources=["serpapi", "remotive", "indeed"]  # Add/remove sources
```

## Monitoring

```bash
# Check scraping jobs via API
curl http://localhost:8000/api/v1/jobs/scraping/

# Count jobs in database
python -c "
from app.core.database import SessionLocal
from app.models.job import Job
db = SessionLocal()
print(f'Total jobs: {db.query(Job).count()}')
"
```

## Production Deployment

### Option 1: Docker Compose (Recommended)

```bash
docker-compose up -d
```

This starts:
- Redis
- Celery Worker
- Celery Beat

### Option 2: Supervisor

See [docs/AUTOMATED_JOB_SCRAPING.md](docs/AUTOMATED_JOB_SCRAPING.md) for systemd/supervisor configs.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Start Redis: `systemctl start redis` |
| No jobs scraped | Check SerpAPI key in `.env` |
| Tasks not running | Restart Celery worker & beat |

## Documentation

- 📖 **Full Guide**: [docs/AUTOMATED_JOB_SCRAPING.md](docs/AUTOMATED_JOB_SCRAPING.md)
- 🚀 **Quick Start**: [QUICK_START_SCHEDULER.md](QUICK_START_SCHEDULER.md)

## Manual Trigger

Test without waiting 3 days:

```python
from app.tasks.periodic_tasks import scheduled_tech_job_scraping
result = scheduled_tech_job_scraping()
print(result)
```

## Cost

- **Redis**: Free (self-hosted) or $5-10/month (managed)
- **SerpAPI**: $50/month for unlimited searches
- **Remotive**: Free (public API)
- **Server**: Minimal overhead (runs on existing backend)

## Benefits

- ✅ No manual scraping needed
- ✅ Always fresh job listings
- ✅ Better user experience
- ✅ Scales automatically
- ✅ Production-ready
