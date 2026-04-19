# Auto-Deletion of Old Jobs (>7 Days)

## Overview

The system now automatically deletes jobs older than 7 days to keep the database fresh, performant, and relevant.

## Why 7 Days?

1. **Relevance**: Most jobs get filled within 1-2 weeks. Jobs older than 7 days are likely closed or no longer active.
2. **Performance**: Smaller database = faster queries, especially for recommendations
3. **Cost**: Reduces database storage costs
4. **User Experience**: Users only see fresh, active job opportunities
5. **Consistency**: Recommendation generator uses 7-day window, so jobs should match

## How It Works

### Automatic Daily Cleanup

The scheduler automatically runs cleanup at **12:10 AM UTC** every night:

```
Midnight UTC (00:00) Schedule:
├── 00:00 - Cleanup expired saved jobs
├── 00:05 - Cleanup expired recommendations
└── 00:10 - Delete jobs older than 7 days ✅
```

**What gets deleted:**
- **Scraped jobs only** where `scraped_at < NOW() - 7 days` (user-added external jobs are never deleted)
- Jobs with saved/applied applications are skipped
- This happens BEFORE the daily scraping at 6 AM
- Fresh jobs come in at 6 AM, old jobs are already gone

**Fallback:** Cleanup also runs **after every scheduled scrape** (every 3 days at 6 AM UTC). So even if the process isn’t running at midnight, the next scrape will remove old jobs.

### Database Flow

```
Day 0: Job scraped → stored in DB
Day 1-6: Job visible, used in recommendations
Day 7: Job still visible (exactly 7 days old)
Day 8+: Job deleted at midnight (>7 days old)
```

### Production Schedule

```
Timeline (UTC):
00:10 AM - Delete old jobs (>7 days)
06:00 AM - Scrape fresh jobs (posted within 2 days)
07:00 AM - Generate recommendations (using jobs from last 7 days)

Result: Database always contains 5-9 days of fresh jobs
```

### Production: Why cleanup might not run at midnight

The in-process scheduler only runs when the **backend process is running at 00:10 UTC**. On many hosts (Render, Railway, Fly.io, Heroku):

- The process may **sleep** or **restart** and miss the midnight window
- There may be **no 24/7 guarantee** that the app is up at that exact time

**What we do about it:**

1. **Cleanup after every scrape** – When the scheduler runs a scrape (every 3 days at 6 AM UTC), it also runs cleanup. So old jobs are removed even if midnight never ran.
2. **HTTP endpoint for external cron** – You can call `POST /api/v1/jobs/cleanup-old` from an external cron (e.g. [cron-job.org](https://cron-job.org)) so cleanup runs even when the app isn’t up at midnight. If you set `CRON_SECRET` in the environment, send it as header: `X-Cron-Secret: <CRON_SECRET>`.

## Manual Cleanup

### Option 1: Run Cleanup Script

Delete old jobs immediately without waiting for scheduler:

```bash
cd backend
python cleanup_old_jobs.py
```

**What it does:**
- Shows you which jobs will be deleted
- Asks for confirmation (type `yes`)
- Deletes all jobs older than 7 days
- Shows statistics

**Example output:**
```
⚠️  Found 14 old jobs to delete:

   Sample jobs to be deleted:
   1. Senior Frontend Engineer at Arize AI
      Scraped: 2025-12-15 (26 days ago)
   ...

⚠️  Delete these jobs? (yes/no): yes

✅ CLEANUP COMPLETED: Deleted 14 old jobs
💾 Total jobs remaining: 0
```

### Option 2: HTTP endpoint (for external cron)

Trigger cleanup from an external cron (e.g. daily at 00:15 UTC):

```bash
curl -X POST "https://your-api.com/api/v1/jobs/cleanup-old" \
  -H "X-Cron-Secret: YOUR_CRON_SECRET"
```

Set `CRON_SECRET` in your environment; if set, the request must include the same value in the `X-Cron-Secret` header. If `CRON_SECRET` is not set, the endpoint accepts requests without the header (useful for dev only).

### Option 3: SQL Query (Supabase)

Run directly in Supabase SQL Editor (only scraped jobs; exclude external):

```sql
-- Preview jobs to be deleted (scraped only)
SELECT
    id,
    title,
    company,
    source,
    scraped_at,
    NOW() - scraped_at AS age
FROM jobs
WHERE scraped_at < NOW() - INTERVAL '7 days'
  AND source != 'external'
ORDER BY scraped_at ASC
LIMIT 20;

-- Delete scraped jobs older than 7 days (keep external jobs)
DELETE FROM jobs
WHERE scraped_at < NOW() - INTERVAL '7 days'
  AND source != 'external';

-- Verify remaining jobs
SELECT
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE scraped_at >= NOW() - INTERVAL '7 days') as recent_jobs,
    MIN(scraped_at) as oldest_job,
    MAX(scraped_at) as newest_job
FROM jobs;
```

### Option 4: Python Code

```python
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.job import Job

db = SessionLocal()

# Delete old jobs
cutoff = datetime.utcnow() - timedelta(days=7)
old_jobs = db.query(Job).filter(Job.scraped_at < cutoff).all()

for job in old_jobs:
    db.delete(job)

db.commit()
print(f"Deleted {len(old_jobs)} old jobs")
db.close()
```

## Implementation Details

### Code Location

**File:** `backend/app/scheduler/job_scheduler.py`

**Function:** `cleanup_old_jobs()`

```python
async def cleanup_old_jobs(self):
    """
    Delete jobs older than 7 days.

    Runs daily at midnight to keep database fresh and performant.
    Only keeps recent jobs that are still relevant.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=7)

    old_jobs = db.query(Job).filter(
        Job.scraped_at < cutoff_date
    ).all()

    for job in old_jobs:
        db.delete(job)

    db.commit()
```

### Scheduler Configuration

```python
self.scheduler.add_job(
    func=self.cleanup_old_jobs,
    trigger=CronTrigger(hour=0, minute=10),  # 12:10 AM UTC
    id="daily_old_jobs_cleanup",
    name="Daily Old Jobs Cleanup (>7 days)",
    replace_existing=True,
    max_instances=1,
)
```

## Impact on Other Features

### ✅ Recommendations
- **No impact** - recommendations already use 7-day window
- System only generates recommendations from jobs <7 days old
- Deleting older jobs keeps database aligned with recommendation logic

### ✅ Saved Jobs
- **No impact** - saved jobs are stored in `applications` table
- Users can save jobs and keep them for 10 days
- Even if original job is deleted, saved reference remains

### ✅ Applications
- **No impact** - applications are independent records
- User's application history is preserved
- Job details are stored in application record

### ✅ Job Search
- **Positive impact** - faster queries with smaller table
- Users only see fresh jobs anyway
- Search results are more relevant

## Monitoring

### Check Cleanup Logs

Backend logs at midnight will show:

```
================================================================================
🧹 CLEANUP: Old Jobs (>7 days)
⏰ Time: 2026-01-11 00:10:00 UTC
================================================================================
📅 Deleting jobs scraped before: 2026-01-04 00:10:00 UTC
✅ CLEANUP COMPLETED: Deleted 14 old jobs
💾 Database now contains only jobs from last 7 days
================================================================================
```

### Query Database Stats

```sql
-- Jobs by age
SELECT
    CASE
        WHEN scraped_at >= NOW() - INTERVAL '1 day' THEN '<1 day'
        WHEN scraped_at >= NOW() - INTERVAL '3 days' THEN '1-3 days'
        WHEN scraped_at >= NOW() - INTERVAL '7 days' THEN '3-7 days'
        ELSE '>7 days (SHOULD BE DELETED)'
    END AS age_group,
    COUNT(*) as count
FROM jobs
GROUP BY age_group
ORDER BY age_group;
```

## Configuration

### Change Retention Period

If you want to keep jobs longer (or shorter), modify `days=7` in two places:

1. **Scheduler cleanup** (`job_scheduler.py` line 202):
   ```python
   cutoff_date = datetime.utcnow() - timedelta(days=7)  # Change this
   ```

2. **Recommendation generator** (`recommendation_generator.py` line 53):
   ```python
   cutoff_date = datetime.utcnow() - timedelta(days=7)  # Change this too
   ```

**Recommended values:**
- **3 days**: Very fresh, aggressive cleanup (production)
- **7 days**: Balanced (default, recommended)
- **14 days**: Conservative, more historical data
- **30+ days**: Not recommended (database bloat)

## Testing

### Test the Cleanup

1. **Check current jobs:**
   ```bash
   cd backend
   python check_database.py
   ```

2. **Run cleanup:**
   ```bash
   python cleanup_old_jobs.py
   ```

3. **Verify deletion:**
   ```bash
   python check_database.py
   ```

### Test the Scheduler

1. **Start backend** (scheduler runs automatically)
2. **Wait for midnight UTC** (00:10)
3. **Check logs** for cleanup messages
4. **Query database** to verify deletion

## FAQ

### Q: What if all my jobs get deleted?

**A:** That's expected if all jobs are >7 days old. Fresh jobs will come in at:
- **6 AM UTC daily** via scheduler
- **Manual scraping** via API/frontend anytime

### Q: Can I disable auto-deletion?

**A:** Yes, but not recommended. Remove the scheduler job in `job_scheduler.py`:

```python
# Comment out or remove this:
# self.scheduler.add_job(
#     func=self.cleanup_old_jobs,
#     ...
# )
```

### Q: What happens to saved jobs?

**A:** Saved jobs are stored separately in `applications` table with their own expiry (10 days). They're not affected by job deletion.

### Q: Why not use database CASCADE?

**A:** We use explicit deletion for better logging, control, and to prevent accidental data loss. This approach is more auditable.

### Q: Can I recover deleted jobs?

**A:** No, deletion is permanent. However:
- Jobs are typically available on original sources
- Scheduler will re-scrape if job is still active
- Application/saved job details are preserved separately

## Benefits

✅ **Performance**: Faster queries, smaller indexes
✅ **Relevance**: Only fresh, active jobs shown
✅ **Cost**: Reduced database storage
✅ **Simplicity**: No manual maintenance needed
✅ **Consistency**: Aligns with recommendation logic
✅ **User Experience**: Better job quality

---

## Summary

- ⏰ **Schedule**: Daily at 12:10 AM UTC
- 📅 **Retention**: 7 days
- 🗑️ **Action**: Auto-delete old jobs
- 🔄 **Flow**: Delete → Scrape → Recommend
- 💾 **Result**: Database always fresh
- ✅ **Status**: Production-ready

No manual intervention needed - system maintains itself automatically!
