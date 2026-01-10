# Next Steps: Get Recommendations Working

## Current Situation

✅ You have 1 CV uploaded
✅ You have 14 jobs in database
❌ BUT those 14 jobs are older than 7 days
✅ Auto-deletion system is now implemented

## The Problem

The recommendation generator only uses jobs from the **last 7 days**. Your 14 existing jobs are too old, so they were skipped when you ran `generate_recommendations.py`.

## Solution: Choose One Option

---

### Option 1: Clean Up Old Jobs + Scrape Fresh Ones (Recommended)

This is the production-ready approach:

#### Step 1: Delete old jobs
```bash
cd backend
python cleanup_old_jobs.py
```
Type `yes` when prompted. This will delete your 14 old jobs.

#### Step 2: Scrape fresh jobs

**Via Frontend:**
1. Go to your dashboard
2. Navigate to Jobs page
3. Look for "Scrape Jobs" button
4. Configure and start scraping
5. Wait 1-2 minutes

**Or via browser console** (while logged in):
```javascript
fetch('/api/v1/jobs/scrape', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    sources: ["adzuna"],  // Free source
    keywords: ["software engineer", "developer", "python"],
    location: "Remote",
    max_results_per_source: 50
  })
}).then(r => r.json()).then(console.log)
```

#### Step 3: Generate recommendations
```bash
python generate_recommendations.py
```

#### Step 4: Test in frontend
1. Go to Jobs page
2. Click "Recommended for You" tab
3. See instant recommendations with match scores!

---

### Option 2: Wait for Scheduler (No Work)

The scheduler will automatically:
- **12:10 AM UTC tonight**: Delete your 14 old jobs
- **6:00 AM UTC tomorrow**: Scrape fresh jobs
- **7:00 AM UTC tomorrow**: Generate recommendations

**No action needed** - just wait ~18 hours.

---

### Option 3: Quick Test with Existing Jobs (Not Recommended)

If you want to test with your existing 14 old jobs without scraping fresh ones:

⚠️ **This is ONLY for testing. Change it back afterward!**

Edit `backend/app/services/recommendation_generator.py` line 53:

**Before:**
```python
cutoff_date = datetime.utcnow() - timedelta(days=7)
```

**After (TEMPORARY):**
```python
cutoff_date = datetime.utcnow() - timedelta(days=365)  # TESTING ONLY
```

Then run:
```bash
python generate_recommendations.py
```

**Remember to change it back to `days=7` after testing!**

---

## Auto-Deletion System (NEW)

Your system now automatically maintains itself:

### Daily Schedule (UTC)
```
00:00 - Delete expired saved jobs (10+ days)
00:05 - Delete expired recommendations (3+ days)
00:10 - Delete old jobs (7+ days) ✅ NEW
06:00 - Scrape fresh jobs
07:00 - Generate recommendations
```

### Benefits
✅ Database always fresh (only 7 days of jobs)
✅ Better performance (smaller tables)
✅ More relevant jobs for users
✅ Aligns with recommendation logic
✅ No manual maintenance needed

### Manual Cleanup
```bash
cd backend
python cleanup_old_jobs.py  # Delete old jobs now
```

---

## Recommendation

**Use Option 1** for immediate testing with production-ready setup:

1. Clean up old jobs → Get fresh jobs → Generate recommendations → Test

This gives you:
- Real testing with fresh jobs
- Production-ready workflow
- Clean database
- Instant recommendations

---

## Documentation

- [GET_FRESH_JOBS_THEN_RECOMMENDATIONS.md](GET_FRESH_JOBS_THEN_RECOMMENDATIONS.md) - Detailed guide
- [docs/AUTO_JOB_DELETION.md](docs/AUTO_JOB_DELETION.md) - Auto-deletion system
- [GENERATE_INITIAL_RECOMMENDATIONS.md](GENERATE_INITIAL_RECOMMENDATIONS.md) - All generation options
- [PRE_COMPUTED_RECOMMENDATIONS_IMPLEMENTATION.md](PRE_COMPUTED_RECOMMENDATIONS_IMPLEMENTATION.md) - Full implementation

---

## Quick Commands Reference

```bash
# Check database status
cd backend
python check_database.py

# Clean up old jobs
python cleanup_old_jobs.py

# Generate recommendations (after you have fresh jobs)
python generate_recommendations.py

# Run backend (scheduler starts automatically)
uvicorn app.main:app --reload
```

---

## What Happens Next

Once you have fresh jobs and generate recommendations:

1. **Today**: Manual generation when you have fresh jobs
2. **Tomorrow**: Scheduler maintains everything automatically
3. **Daily**: Old jobs deleted, fresh jobs scraped, recommendations generated
4. **Users**: Always see fresh, relevant opportunities

Your system is now production-ready with automatic maintenance! 🚀
