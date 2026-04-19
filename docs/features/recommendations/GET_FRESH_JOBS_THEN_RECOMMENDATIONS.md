# Get Fresh Jobs, Then Generate Recommendations

## Diagnosis Results

✅ You have 1 CV uploaded
✅ You have 14 jobs in database
❌ **BUT** those 14 jobs are older than 7 days

**The recommendation generator only uses jobs from the last 7 days** to ensure fresh, relevant recommendations.

---

## Solution: Get Fresh Jobs First

You have **two options**:

---

### Option 1: Wait for Scheduler (Automatic)

The scheduler will automatically scrape fresh jobs at **6:00 AM UTC** tomorrow, then generate recommendations at **7:00 AM UTC**.

**No action needed** - just wait.

---

### Option 2: Manual Scraping (Immediate)

Trigger job scraping now via the frontend or API.

#### Method A: Via Frontend (Easiest)

1. Go to your Jobs page
2. Look for the "Scrape Jobs" button/form
3. Configure sources and keywords
4. Click "Start Scraping"
5. Wait 1-2 minutes for jobs to be scraped
6. Then run: `python generate_recommendations.py`

#### Method B: Via API (Browser Console)

While logged into your dashboard, open browser console and run:

```javascript
// Trigger job scraping
fetch('/api/v1/jobs/scrape', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    sources: ["adzuna", "indeed"],  // or your available sources
    keywords: ["software engineer", "developer", "python"],  // your job interests
    location: "Remote",
    max_results_per_source: 50
  })
})
.then(r => r.json())
.then(data => {
  console.log('Scraping started:', data)
  alert('✅ Job scraping started! Check status in 1-2 minutes.')
})
```

#### Method C: Via curl

```bash
curl -X POST http://localhost:8000/api/v1/jobs/scrape \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["adzuna", "indeed"],
    "keywords": ["software engineer", "developer"],
    "location": "Remote",
    "max_results_per_source": 50
  }'
```

---

## After Scraping Completes

1. **Verify fresh jobs exist:**
   ```bash
   cd backend
   python check_database.py
   ```
   Should show: "Jobs from last 7 days: X" (where X > 0)

2. **Generate recommendations:**
   ```bash
   python generate_recommendations.py
   ```

3. **Test in frontend:**
   - Go to Jobs page
   - Click "Recommended for You" tab
   - Should see recommendations with match scores!

---

## Alternative: Modify Time Window (Quick Fix for Testing)

If you want to use the existing 14 jobs for testing without waiting for new scrapes, you can temporarily modify the recommendation generator:

**File:** `backend/app/services/recommendation_generator.py`

Find this line (around line 50):
```python
days_back = 7
```

Change it to:
```python
days_back = 365  # Use all jobs for testing
```

Then run:
```bash
python generate_recommendations.py
```

**Remember to change it back to 7 after testing!**

---

## Summary

**Problem:** Your 14 jobs are older than 7 days, so recommendation generator skips them.

**Solution:**
1. **Quick test**: Change `days_back = 365` temporarily
2. **Proper fix**: Scrape fresh jobs first, then generate recommendations
3. **Production**: Wait for scheduler to run at 6 AM UTC daily

---

## Questions?

Run the diagnostic anytime:
```bash
cd backend
python check_database.py
```

This will show you current status of CVs and jobs.
