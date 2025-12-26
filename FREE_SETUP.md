# 100% Free Job Scraping Setup

This platform now uses **completely free** job scraping sources - no paid APIs required!

## Free Sources

### 1. Remotive API
- **Cost**: $0 (Free public API)
- **Coverage**: Remote jobs worldwide
- **No API key needed**
- **~200 jobs per scrape**

### 2. RemoteOK API
- **Cost**: $0 (Free public API)
- **Coverage**: Remote jobs worldwide
- **No API key needed**
- **~200 jobs per scrape**

## Total Costs

- **API Costs**: $0/month
- **Infrastructure**: Free (self-hosted Redis) or ~$5-10/month (managed Redis)
- **Expected Jobs**: 400-600 new tech jobs every 3 days

## What Gets Scraped Automatically

Every 3 days at 2 AM UTC, the system automatically scrapes:

### 20+ Tech Job Categories

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

## Quick Start

### Option 1: Docker (Easiest)

```bash
# Start everything (Redis + Celery Worker + Celery Beat)
docker-compose up -d

# View logs
docker-compose logs -f celery_worker
```

### Option 2: Manual

```bash
# Terminal 1: Start Redis
sudo systemctl start redis

# Terminal 2: Start Celery Worker
cd backend
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

# Terminal 3: Start Celery Beat
cd backend
celery -A app.tasks.celery_app beat --loglevel=info
```

## Test Manually

Don't want to wait 3 days? Trigger a scrape now:

```python
cd backend
python << 'EOF'
from app.tasks.periodic_tasks import scheduled_tech_job_scraping

# Trigger immediately
result = scheduled_tech_job_scraping()
print(f"Scraping started: {result}")
EOF
```

## Verify It's Working

Check your database:

```python
cd backend
python << 'EOF'
from app.core.database import SessionLocal
from app.models.job import Job

db = SessionLocal()
count = db.query(Job).count()
print(f"Total jobs in database: {count}")

# Show latest jobs
latest = db.query(Job).order_by(Job.created_at.desc()).limit(5).all()
for job in latest:
    print(f"- {job.title} at {job.company} (source: {job.source})")

db.close()
EOF
```

## Why Free Sources Only?

- **No vendor lock-in**: Not dependent on paid services
- **Unlimited scaling**: No API quota limits to worry about
- **Production-ready**: Perfect for MVPs and growing platforms
- **Good coverage**: 400+ jobs every 3 days is plenty for most use cases

## Upgrading Later

If you need more coverage in the future, you can add paid sources like SerpAPI:

```python
# In backend/app/tasks/periodic_tasks.py
sources=["remotive", "remoteok", "serpapi"]  # Add serpapi

# Set API key in .env
SERPAPI_API_KEY=your_key_here
```

But for now, **free sources work great!**

## Documentation

- Quick Start: [QUICK_START_SCHEDULER.md](QUICK_START_SCHEDULER.md)
- Full Documentation: [docs/AUTOMATED_JOB_SCRAPING.md](docs/AUTOMATED_JOB_SCRAPING.md)

## Next Steps

1. ✅ Start Redis, Celery Worker, and Celery Beat
2. ✅ Test manually to verify it works
3. ✅ Let it run automatically every 3 days
4. ✅ Watch your job database grow with fresh tech jobs!

---

**Total Monthly Cost**: $0 for APIs + ~$0-10 for Redis (can be self-hosted for free)
