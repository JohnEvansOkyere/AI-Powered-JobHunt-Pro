# Automated Job Scraping Scheduler

## Overview

The job scraping system now uses **APScheduler** to automatically scrape fresh tech jobs **daily at 6:00 AM UTC**.

### Key Features

✅ **Daily Automated Scraping** - Runs every day at 6 AM UTC
✅ **Recent Jobs Only** - Only scrapes jobs posted within last 2 days
✅ **Zero Duplicates** - Smart deduplication prevents duplicate jobs in database
✅ **100% Free** - Uses 3 free sources (Remotive, RemoteOK, Adzuna)
✅ **100+ Tech Keywords** - Comprehensive coverage of all tech roles
✅ **Auto-Start** - Scheduler starts automatically with the backend server

---

## How It Works

### 1. Schedule
- **Frequency**: Daily
- **Time**: 6:00 AM UTC
- **Jobs Scraped**: Posted within last 2 days only

### 2. Sources (All FREE)
1. **Remotive** - Remote jobs worldwide
2. **RemoteOK** - Remote tech jobs
3. **Adzuna** - Job aggregator (thousands of sources)

### 3. Tech Job Categories (100+)

The scheduler searches for jobs in these categories:

- **Software Engineering** (19 keywords)
  - Backend, Frontend, Full Stack, Mobile, Web
  - Python, Java, Node.js, React, .NET, Golang, Ruby

- **Data & AI** (13 keywords)
  - Data Scientist, Data Analyst, Data Engineer
  - ML Engineer, AI Engineer, Deep Learning Engineer
  - NLP Engineer, Computer Vision Engineer

- **DevOps & Infrastructure** (14 keywords)
  - DevOps Engineer, SRE, Platform Engineer
  - Cloud Engineer (AWS, Azure, GCP)
  - Kubernetes, Docker, Systems Engineer

- **Design** (10 keywords)
  - UX Designer, UI Designer, Product Designer
  - Graphic Designer, Web Designer, Visual Designer

- **Product & Management** (7 keywords)
  - Product Manager, Technical PM, Engineering Manager
  - Program Manager, Tech Lead

- **Quality & Testing** (6 keywords)
  - QA Engineer, Test Engineer, Automation Engineer
  - SDET, Performance Engineer

- **Security** (6 keywords)
  - Security Engineer, Cybersecurity Engineer
  - Penetration Tester, Security Analyst

- **Specialized** (7 keywords)
  - Embedded Engineer, Robotics Engineer
  - Blockchain Developer, Game Developer

- **Database & Architecture** (7 keywords)
  - Database Engineer, DBA, Solutions Architect
  - Software Architect, System Architect

### 4. Deduplication

**Prevents duplicate jobs using two methods:**

1. **By Job URL** (most reliable)
   - Checks if `job_link` already exists in database
   - 100% accurate for jobs with unique URLs

2. **By Title + Company** (fuzzy match)
   - Checks if same title + company exists within last 30 days
   - Handles jobs without unique URLs

**Result**: Zero duplicate jobs in your database!

---

## Expected Results

### Daily Scrape Volume
- **Per Source**: ~50-100 jobs
- **Total**: 150-300 fresh jobs daily
- **After Deduplication**: ~50-150 new jobs stored (rest are duplicates)

### Job Freshness
- Only jobs posted within **last 2 days**
- No old/stale jobs cluttering your database
- Database stays fresh and relevant

---

## Usage

### Automatic (Recommended)

The scheduler **starts automatically** when you run the backend server:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

You'll see this in the logs:
```
✅ Job scraper scheduler started successfully
⏰ Schedule: Daily at 6:00 AM UTC
📅 Scrapes jobs posted within last 2 days
🔄 Next run: 2025-12-28 06:00:00 UTC
```

### Manual Trigger (Testing)

You can manually trigger a scrape at any time:

```python
cd backend
python << 'EOF'
import asyncio
from app.scheduler import get_scheduler

async def test_scrape():
    scheduler = get_scheduler()
    result = await scheduler.trigger_manual_scrape()
    print(f"\n✅ Scraping Complete!")
    print(f"   - Total found: {result.get('total_found', 0)}")
    print(f"   - New jobs stored: {result.get('stored', 0)}")
    print(f"   - Duplicates skipped: {result.get('duplicates', 0)}")

asyncio.run(test_scrape())
EOF
```

### Check Scheduler Status

```python
cd backend
python << 'EOF'
from app.scheduler import get_scheduler

scheduler = get_scheduler()
scheduler.start()

# Get next scheduled run time
job = scheduler.scheduler.get_job('daily_job_scraping')
print(f"Next run: {job.next_run_time}")
EOF
```

---

## Configuration

### Change Schedule Time

Edit [backend/app/scheduler/job_scheduler.py](backend/app/scheduler/job_scheduler.py):

```python
# Current: Daily at 6 AM UTC
self.scheduler.add_job(
    func=self.scrape_recent_jobs,
    trigger=CronTrigger(hour=6, minute=0),  # Change hour here
    ...
)

# Example: Run at 2 AM UTC
trigger=CronTrigger(hour=2, minute=0)

# Example: Run twice daily (6 AM and 6 PM)
self.scheduler.add_job(..., trigger=CronTrigger(hour='6,18', minute=0))

# Example: Run every 12 hours
from apscheduler.triggers.interval import IntervalTrigger
trigger=IntervalTrigger(hours=12)
```

### Change Lookback Period (Days)

Edit [backend/app/scheduler/job_scheduler.py](backend/app/scheduler/job_scheduler.py):

```python
# Current: Last 2 days
cutoff_date = datetime.utcnow() - timedelta(days=2)

# Change to 1 day (last 24 hours only)
cutoff_date = datetime.utcnow() - timedelta(days=1)

# Change to 3 days
cutoff_date = datetime.utcnow() - timedelta(days=3)
```

### Add More Tech Keywords

Edit [backend/app/scheduler/job_scheduler.py](backend/app/scheduler/job_scheduler.py):

```python
TECH_JOB_KEYWORDS = [
    # ... existing keywords ...

    # Add your custom keywords
    "your custom role",
    "another role",
]
```

### Change Sources

Edit [backend/app/scheduler/job_scheduler.py](backend/app/scheduler/job_scheduler.py):

```python
# Current: All 3 free sources
sources = ["remotive", "remoteok", "adzuna"]

# Use only specific sources
sources = ["remotive", "remoteok"]  # Skip Adzuna
sources = ["adzuna"]  # Only Adzuna
```

---

## Monitoring

### View Logs

```bash
# Watch scheduler logs in real-time
cd backend
tail -f logs/app.log | grep -i "scraping\|scheduler"
```

You'll see output like:
```
🚀 SCHEDULED JOB SCRAPING STARTED
⏰ Time: 2025-12-28 06:00:00 UTC
📅 Scraping jobs posted after: 2025-12-26 06:00:00 UTC
📡 Sources: remotive, remoteok, adzuna
🔑 Keywords: 100 tech job categories
✅ SCRAPING COMPLETED
📊 Results:
   - Total found: 287
   - New jobs stored: 94
   - Duplicates skipped: 193
   - Failed: 0
```

### Check Database

```bash
cd backend
python << 'EOF'
from app.core.database import SessionLocal
from app.models.job import Job
from datetime import datetime, timedelta

db = SessionLocal()

# Count jobs by date
recent = datetime.utcnow() - timedelta(days=2)
count = db.query(Job).filter(Job.scraped_at >= recent).count()
print(f"Jobs scraped in last 2 days: {count}")

# Count jobs by source
from sqlalchemy import func
by_source = db.query(Job.source, func.count(Job.id)).group_by(Job.source).all()
for source, count in by_source:
    print(f"{source}: {count} jobs")

db.close()
EOF
```

---

## Troubleshooting

### Scheduler Not Starting

**Error**: `Failed to start job scraper scheduler`

**Solutions**:
1. Check APScheduler is installed: `pip install apscheduler`
2. Check backend logs for specific error
3. Verify database is running and accessible

### No Jobs Being Scraped

**Possible Causes**:
1. **Wait for scheduled time** - First run is at 6 AM UTC
2. **Sources may be down** - Check source APIs:
   ```bash
   curl https://remotive.com/api/remote-jobs
   curl https://remoteok.com/api
   ```
3. **All jobs are duplicates** - Check database, may already have recent jobs

### Too Many Duplicates

**Expected Behavior**: High duplicate rate (60-80%) is normal for daily scraping

**Explanation**:
- Most job postings stay active for weeks
- Scraping daily means we see the same jobs multiple times
- Deduplication prevents them from entering database
- This is working as intended!

**Example**:
```
Day 1: 300 found → 150 new jobs stored (50% duplicates)
Day 2: 300 found → 50 new jobs stored (83% duplicates) ✓ Normal!
Day 3: 300 found → 40 new jobs stored (87% duplicates) ✓ Normal!
```

### Memory/Performance Issues

If scheduler uses too much memory:

1. **Reduce lookback period** (2 days → 1 day)
2. **Reduce keywords** (100 → 50 most relevant)
3. **Reduce sources** (3 → 2 sources)
4. **Reduce max_results_per_source** (100 → 50)

---

## Comparison: Celery vs APScheduler

### Why APScheduler?

| Feature | APScheduler | Celery Beat |
|---------|-------------|-------------|
| Setup Complexity | Simple (1 file) | Complex (Redis, worker, beat) |
| Dependencies | 1 package | 3+ packages + Redis |
| Memory Usage | ~20-30 MB | ~100-150 MB |
| Perfect For | Single-server apps | Distributed systems |
| Cost | Free | Free (but need Redis) |

### When to Switch to Celery

Use Celery if you:
- Have multiple backend servers
- Need distributed task processing
- Already use Redis/RabbitMQ
- Need complex task workflows

For most use cases, **APScheduler is perfect** and much simpler!

---

## Files Modified/Created

### Created
- `backend/app/scheduler/__init__.py` - Package init
- `backend/app/scheduler/job_scheduler.py` - Main scheduler implementation

### Modified
- `backend/app/main.py` - Added scheduler startup/shutdown
- `backend/app/services/job_scraper_service.py` - Added `min_posted_date` filtering

---

## Cost

**Total Cost**: **$0/month**

- APScheduler: Free (open source)
- Remotive API: Free
- RemoteOK API: Free
- Adzuna API: Free
- No Redis needed
- No message broker needed

---

## Next Steps

1. ✅ Start backend server - scheduler auto-starts
2. ⏰ Wait for 6 AM UTC or trigger manual scrape
3. 📊 Check logs to verify scraping works
4. 🎯 Customize schedule/keywords if needed
5. 🚀 Jobs automatically flow into "Recommended for You" tab!

---

**Your job scraping is now fully automated! 🎉**

The scheduler will keep your database fresh with new tech jobs daily, and the AI matcher will recommend the best ones to your users.
