# Application-Aware Job Cleanup Strategy

## Overview

Smart database cleanup that **preserves user application history** while keeping the database lean.

## The Strategy

### ✅ Jobs WITH Applications (User Applied)
```
User applies to job
    ↓
Application record created
    ↓
Job KEPT FOREVER (for tracking)
```

**Why?**
- Users need to track their application history
- Reference job details months later
- See which companies they applied to
- Track application status

### ❌ Jobs WITHOUT Applications (Nobody Cared)
```
Job scraped
    ↓
Day 1-7: Available for matching
    ↓
Day 7: No applications → DELETED
```

**Why?**
- Keeps database lean and fast
- Removes job noise from searches
- Saves storage costs
- Only keeps relevant jobs

## Implementation

### Script Location
`backend/scripts/cleanup_old_jobs.py`

### What It Does

1. **Checks all jobs older than 7 days**
2. **Filters to jobs with NO applications**
3. **Deletes those jobs** and their matches
4. **Keeps all jobs** that have applications

### Database Queries

**Find unapplied old jobs:**
```sql
SELECT * FROM jobs
WHERE created_at < NOW() - INTERVAL '7 days'
  AND id NOT IN (SELECT DISTINCT job_id FROM applications);
```

**Jobs kept forever:**
```sql
SELECT * FROM jobs
WHERE id IN (SELECT DISTINCT job_id FROM applications);
```

## Benefits

### For Users
- ✅ **Never lose application history**
- ✅ Track which jobs they applied to
- ✅ Reference job descriptions months later
- ✅ See application timeline

### For System
- ✅ **Lean database** - only keeps relevant jobs
- ✅ **Fast queries** - less data to scan
- ✅ **Lower costs** - reduced storage
- ✅ **Better UX** - less clutter in job searches

## Statistics

The cleanup script shows detailed stats:

```
📊 Database Statistics:
======================================================================
  Total jobs: 150
  ├─ Jobs with applications (kept): 25
  └─ Jobs without applications: 125
       └─ Old unapplied jobs (>7 days): 50 (will be deleted)

  Total applications: 25
  Cached job matches: 300
======================================================================
```

This example shows:
- 150 total jobs
- 25 have applications → **KEPT FOREVER**
- 50 are old and unapplied → **WILL BE DELETED**
- 75 are new (< 7 days) → kept for now

## Running the Cleanup

### Manually
```bash
cd backend
python scripts/cleanup_old_jobs.py
```

### Automated (Daily at 3 AM)
```bash
cd backend
./scripts/setup_cron_jobs.sh
```

### View Logs
```bash
tail -f logs/job_cleanup.log
```

## Configuration

Edit `scripts/cleanup_old_jobs.py` to adjust thresholds:

```python
# How long to keep unapplied jobs (default: 7 days)
delete_unapplied_old_jobs(db, days_old=7)

# How long to keep match cache (default: 90 days)
clean_old_matches(db, days_to_keep=90)
```

## Examples

### Example 1: User Applied to Job
```
Day 0:  Job "Senior Engineer at Google" scraped
Day 1:  User generates application → Application record created
Day 7:  Cleanup runs → Job KEPT (has application)
Day 30: Job STILL KEPT
Day 90: Job STILL KEPT
...forever: Job STILL KEPT for user's tracking
```

### Example 2: User Didn't Apply
```
Day 0:  Job "Junior Developer at StartupX" scraped
Day 1:  Job appears in user's matches (50% score)
Day 2:  User views job but doesn't apply
Day 7:  Cleanup runs → Job DELETED (no application)
```

### Example 3: Multiple Users
```
Day 0:  Job "Data Scientist at TechCo" scraped
Day 1:  User A applies → Application created
Day 3:  User B views but doesn't apply
Day 7:  Cleanup runs → Job KEPT (User A has application)

Result: User A keeps tracking, User B doesn't see it anymore
```

## Database Tables Affected

### `jobs`
- Jobs WITH applications: Kept forever
- Jobs WITHOUT applications: Deleted after 7 days

### `applications`
- Never deleted automatically
- User controls their application history

### `job_matches`
- Cache entries cleaned after 90 days
- Regenerated when user searches

## Monitoring

### Check what will be deleted
```bash
cd backend
python << 'EOF'
from app.core.database import get_db
from app.models.job import Job
from app.models.application import Application
from datetime import datetime, timedelta

db = next(get_db())

cutoff = datetime.utcnow() - timedelta(days=7)

unapplied_old = db.query(Job).filter(
    Job.created_at < cutoff,
    ~Job.id.in_(db.query(Application.job_id).distinct())
).all()

print(f"Jobs to be deleted: {len(unapplied_old)}")
for job in unapplied_old[:10]:
    print(f"  - {job.title} at {job.company} (created {job.created_at})")
EOF
```

### Check user's applications
```bash
cd backend
python << 'EOF'
from app.core.database import get_db
from app.models.application import Application
from app.models.job import Job

db = next(get_db())

apps = db.query(Application).all()

print(f"Total applications: {len(apps)}")
for app in apps[:10]:
    job = db.query(Job).filter(Job.id == app.job_id).first()
    if job:
        print(f"  - {job.title} at {job.company} (applied {app.created_at})")
EOF
```

## FAQ

**Q: What if I want to keep jobs longer than 7 days?**
A: Edit `cleanup_old_jobs.py` and change `days_old=7` to `days_old=30` or whatever you want.

**Q: Can users see deleted jobs?**
A: No. Once deleted, they're gone. But jobs they applied to are never deleted.

**Q: What about jobs from 6 months ago?**
A: If user applied, it's still there. If not, it was deleted after 7 days.

**Q: Does this affect job scraping?**
A: No. New jobs are scraped daily regardless of cleanup.

**Q: What if a job is deleted but I want to apply?**
A: Jobs older than 7 days are usually no longer accepting applications anyway. Fresh jobs (<7 days) are always available.

## Summary

**Smart cleanup that:**
- ✅ Preserves what matters (user applications)
- ✅ Removes what doesn't (unapplied old jobs)
- ✅ Keeps database fast and lean
- ✅ Gives users full application tracking

**Result:**
- Users never lose their application history
- Database doesn't grow indefinitely with irrelevant jobs
- Win-win for both UX and performance! 🎉
