# Job Seeding Guide - Quick Fix

## The Problem

The scrapers are failing because:
1. **Remotive API**: Returns 526 error when query string is too long (too many keywords)
2. **SerpAPI**: Returns 400 Bad Request for the same reason

## Solutions (3 Scripts Available)

### Option 1: Simple Script (RECOMMENDED) ✅

**File**: `seed_jobs_simple.py`

**What it does**:
- Fetches ALL jobs from Remotive (no search query)
- Most reliable - no query parameter issues
- Gets ~200-500 jobs typically

**Run**:
```bash
cd /home/grejoy/Projects/AI-Powered-JobHunt-Pro/backend
python seed_jobs_simple.py
```

**Expected output**:
```
✅ Received 300 jobs from Remotive
✅ SUCCESS! Added 300 new jobs to database
```

---

### Option 2: Improved Script

**File**: `seed_jobs_improved.py`

**What it does**:
- Uses multiple smaller queries (one keyword at a time)
- Fetches from both Remotive and SerpAPI
- More targeted results

**Run**:
```bash
python seed_jobs_improved.py
```

---

### Option 3: Original Script

**File**: `seed_jobs.py`

**What it does**:
- Uses all keywords in one query (causes the error you saw)
- Keep for reference but use Option 1 or 2 instead

---

## Recommended Approach

**Try in this order:**

1. **First, try the simple script:**
   ```bash
   python seed_jobs_simple.py
   ```
   - Should get ~300 jobs
   - No API issues
   - Fastest and most reliable

2. **If that fails, wait 5 minutes and try again:**
   - Remotive might be rate limiting
   - Try from a different network if possible

3. **Alternative: Use the improved script:**
   ```bash
   python seed_jobs_improved.py
   ```
   - Makes smaller, targeted queries
   - Less likely to hit rate limits

---

## Verification

After running the script successfully:

### 1. Check Database (Supabase SQL Editor)

```sql
-- Count jobs
SELECT COUNT(*) FROM jobs;

-- See recent jobs
SELECT title, company, source, created_at
FROM jobs
ORDER BY created_at DESC
LIMIT 10;

-- Jobs by source
SELECT source, COUNT(*) as count
FROM jobs
GROUP BY source;
```

Expected:
```
COUNT: 300+
SOURCE: remotive
```

### 2. Test API

```bash
curl http://localhost:8000/api/v1/jobs/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Should return jobs array with ~300 jobs.

### 3. Check Frontend

Visit: `http://localhost:3000/dashboard/jobs`

Should see:
- List of jobs
- Match scores
- Company names
- Locations

---

## Troubleshooting

### Error: "526 Server Error" or "400 Bad Request"

**Cause**: Query too long or rate limiting

**Solution**:
1. Use `seed_jobs_simple.py` instead (no query)
2. Wait 5-10 minutes
3. Try again

### Error: "No jobs fetched"

**Cause**: Network issue or Remotive is down

**Solution**:
1. Check internet connection
2. Test Remotive API manually:
   ```bash
   curl https://remotive.io/api/remote-jobs
   ```
3. If above works but script fails, check firewall/proxy

### Error: "Database connection failed"

**Cause**: DATABASE_URL incorrect in .env

**Solution**:
1. Check `.env` file has correct DATABASE_URL
2. Test connection:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

### Jobs saved but not showing in frontend

**Cause**: Jobs need to be processed and matched

**Solution**:
1. Check job processing_status:
   ```sql
   SELECT processing_status, COUNT(*)
   FROM jobs
   GROUP BY processing_status;
   ```
2. Jobs start as "pending" - matching happens automatically
3. Wait a few seconds and refresh frontend

---

## Manual Testing

Test Remotive API directly:

```bash
# Fetch all jobs (no search)
curl https://remotive.io/api/remote-jobs | jq '.jobs | length'

# Should return: 200-500

# Fetch with simple search
curl 'https://remotive.io/api/remote-jobs?search=python' | jq '.jobs | length'

# Should return: 50-100
```

---

## Next Steps After Successful Seeding

1. **Verify Jobs in Database**:
   ```sql
   SELECT COUNT(*) FROM jobs;  -- Should be 300+
   ```

2. **Visit Frontend**:
   ```
   http://localhost:3000/dashboard/jobs
   ```

3. **Check Job Matching**:
   - Jobs will be automatically matched based on user profile
   - Match scores calculated using skills, experience, preferences

4. **Set Up Periodic Scraping** (Optional):
   - Configure Celery Beat for daily scraping
   - See `docs/JOB_SCRAPING_ISSUE_RESOLUTION.md` for details

---

## Summary

**Problem**: Query string too long for Remotive/SerpAPI
**Solution**: Use `seed_jobs_simple.py` (no search query)
**Expected Result**: ~300 jobs from Remotive
**Time**: 30-60 seconds

**Command**:
```bash
cd /home/grejoy/Projects/AI-Powered-JobHunt-Pro/backend
python seed_jobs_simple.py
```

---

**Updated**: December 24, 2025
**Author**: Claude Sonnet 4.5
