# Quick Start: Automated Job Scraping

Get the automated job scraper running in 5 minutes!

## Prerequisites

- Redis installed and running
- Python environment activated
- Backend `.env` configured with API keys

## Start in 3 Steps

### 1. Start Redis

```bash
# Check if Redis is running
redis-cli ping

# If not running, start it:
sudo systemctl start redis   # Linux
brew services start redis    # macOS
```

### 2. Start Celery Worker

Open a new terminal:

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
```

Keep this terminal open.

### 3. Start Celery Beat (Scheduler)

Open another terminal:

```bash
cd backend
celery -A app.tasks.celery_app beat --loglevel=info
```

Keep this terminal open.

## ✅ Done!

The scraper is now running and will automatically scrape tech jobs **every 3 days at 2 AM UTC**.

## Test It Manually

To test without waiting 3 days:

```python
cd backend
python << 'EOF'
from app.tasks.periodic_tasks import scheduled_tech_job_scraping

# Trigger immediately
result = scheduled_tech_job_scraping()
print(f"Scraping started: {result}")
EOF
```

## Monitor Progress

Watch the Celery Worker terminal for logs like:

```
[INFO] Starting scheduled tech job scraping...
[INFO] Created scraping job abc-123 for scheduled tech job scraping
[INFO] SerpAPI: fetched 50 jobs for query='software engineer'
[INFO] Remotive: fetched 30 jobs for query='data scientist'
[INFO] Stored 75 new jobs (5 duplicates skipped)
```

## Check Results

```bash
# Count jobs in database
cd backend
python << 'EOF'
from app.core.database import SessionLocal
from app.models.job import Job

db = SessionLocal()
count = db.query(Job).count()
print(f"Total jobs: {count}")
db.close()
EOF
```

## Using Docker (Alternative)

Prefer Docker? Just run:

```bash
docker-compose up -d
docker-compose logs -f celery_worker
```

## Troubleshooting

**"Connection refused to Redis"**
→ Start Redis: `sudo systemctl start redis`

**"No module named 'celery'"**
→ Install: `pip install celery redis`

**"Task not registered"**
→ Restart Celery worker and beat

## What's Being Scraped?

- **20+ tech job categories** (engineers, data scientists, designers, etc.)
- **2 FREE sources**: Remotive + RemoteOK (no API keys needed)
- **~200 jobs per source** = 400+ new jobs every 3 days
- **Worldwide coverage** with focus on remote/hybrid roles

## Next Steps

1. ✅ Verify scraping works manually (test command above)
2. ✅ Let it run automatically (it will scrape every 3 days)
3. ✅ Check your frontend - new jobs will appear!
4. 📝 Customize keywords in `backend/app/tasks/periodic_tasks.py`
5. 📝 Adjust schedule in `periodic_tasks.py` if needed

For detailed docs, see: [docs/AUTOMATED_JOB_SCRAPING.md](docs/AUTOMATED_JOB_SCRAPING.md)
