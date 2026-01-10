# How to Generate Initial Recommendations

The recommendations database is currently empty because the scheduler runs daily at **7:00 AM UTC**. Here are multiple ways to populate recommendations immediately for testing:

---

## Option 1: API Endpoint (Easiest - Recommended)

### For Current User Only

Use the new manual trigger endpoint to generate recommendations for yourself:

**Using curl:**
```bash
curl -X POST http://localhost:8000/api/v1/jobs/recommendations/generate \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

**Using Frontend (via browser console):**
```javascript
// In browser console on your dashboard
fetch('/api/v1/jobs/recommendations/generate', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('access_token')
  }
})
.then(r => r.json())
.then(data => console.log(data))
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Generated 50 recommendations",
  "recommendations_count": 50,
  "user_id": "your-user-uuid"
}
```

**What it does:**
- Fetches your latest CV
- Gets jobs from last 7 days
- Runs AI matching
- Stores top 50 matches
- Sets expiry to 3 days from now

**Time:** ~5-10 seconds depending on number of jobs

---

## Option 2: Python Script (For All Users)

Create a script to generate recommendations for ALL users at once:

### Create the script:

**File:** `generate_recommendations.py`

```python
"""
Manual script to generate recommendations for all users.
Run this from the backend directory.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.recommendation_generator import RecommendationGenerator

async def main():
    print("=" * 80)
    print("🎯 MANUAL RECOMMENDATION GENERATION")
    print("=" * 80)

    db = SessionLocal()

    try:
        generator = RecommendationGenerator(db)
        stats = await generator.generate_recommendations_for_all_users()

        print("\n" + "=" * 80)
        print("✅ GENERATION COMPLETED")
        print(f"   Users processed: {stats['successful']}/{stats['total_users']}")
        print(f"   Total recommendations: {stats['total_recommendations']}")
        print(f"   Failed: {stats['failed']}")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Run the script:

```bash
cd backend
python generate_recommendations.py
```

**What it does:**
- Finds all users with CVs
- Generates recommendations for each user
- Shows progress and statistics
- Same logic as the scheduler

**Time:** ~10-30 seconds depending on number of users

---

## Option 3: Python Shell (Interactive Testing)

For quick testing or debugging, use Python shell:

```bash
cd backend
python
```

```python
import asyncio
from app.core.database import SessionLocal
from app.services.recommendation_generator import RecommendationGenerator

# Create database session
db = SessionLocal()

# Create generator
generator = RecommendationGenerator(db)

# Generate for specific user (replace with your user ID)
user_id = "your-user-uuid-here"
count = asyncio.run(generator.generate_recommendations_for_user(user_id))
print(f"Generated {count} recommendations")

# Or generate for all users
stats = asyncio.run(generator.generate_recommendations_for_all_users())
print(stats)

# Close session
db.close()
```

---

## Option 4: Wait for Scheduler (No Action Needed)

The scheduler will automatically run at **7:00 AM UTC** tomorrow and generate recommendations for all users.

**Schedule:**
- **6:00 AM UTC** - Job scraping (gets new jobs)
- **7:00 AM UTC** - Recommendation generation
- **12:05 AM UTC** - Cleanup expired recommendations

**No action required** - just wait until tomorrow morning.

---

## Verification

After generating recommendations, verify they're in the database:

### Via API (Frontend):
1. Go to Jobs page
2. Click "Recommended for You" tab
3. Should see jobs with match scores instantly

### Via Database (Supabase):
```sql
-- Count recommendations per user
SELECT user_id, COUNT(*) as recommendations
FROM job_recommendations
WHERE expires_at > NOW()
GROUP BY user_id;

-- View sample recommendations
SELECT * FROM job_recommendations
ORDER BY match_score DESC
LIMIT 10;
```

### Via Backend Logs:
Look for these log messages:
```
✅ Created 50 recommendations for user abc-123
```

---

## Troubleshooting

### No recommendations generated (count = 0)

**Possible causes:**

1. **No CV uploaded**
   ```sql
   SELECT COUNT(*) FROM cvs WHERE user_id = 'YOUR_USER_ID';
   ```
   **Solution:** Upload a CV first

2. **No jobs in database**
   ```sql
   SELECT COUNT(*) FROM jobs WHERE scraped_at >= NOW() - INTERVAL '7 days';
   ```
   **Solution:** Run job scraper first or wait for scheduled scraping

3. **AI matching error**
   Check backend logs for errors related to OpenAI API

### Error: "No module named 'app'"

**Solution:** Make sure you're in the `backend` directory:
```bash
cd backend
python generate_recommendations.py
```

### Error: "No OpenAI API key"

**Solution:** Ensure `.env` file has:
```
OPENAI_API_KEY=your-key-here
```

---

## Recommended Testing Flow

1. **Ensure you have jobs in the database:**
   ```bash
   # Check job count
   curl http://localhost:8000/api/v1/jobs/?page=1&page_size=10
   ```

2. **Ensure you have a CV uploaded:**
   - Go to Profile → Upload CV

3. **Generate recommendations:**
   - **Option 1 (Fastest):** Call the API endpoint via browser console or curl
   - **Option 2 (All users):** Run the Python script

4. **View recommendations:**
   - Go to Jobs page → "Recommended for You" tab
   - Should load instantly with match scores

5. **Check expiry:**
   - Recommendations expire after 3 days
   - Will be replaced by scheduler at 7 AM UTC daily

---

## Summary

| Method | Speed | Scope | Use Case |
|--------|-------|-------|----------|
| **API Endpoint** | Fastest | Current user | Quick testing, individual users |
| **Python Script** | Fast | All users | Initial population, batch generation |
| **Python Shell** | Medium | Flexible | Debugging, custom queries |
| **Wait for Scheduler** | Slow | All users | Production, automated |

**For immediate testing:** Use **Option 1** (API endpoint) - it's the fastest and easiest.

**For production setup:** Use **Option 2** (Python script) once to populate all users, then let the scheduler handle daily updates.

---

## Next Steps

After generating recommendations:

1. Test the "Recommended for You" tab - should load instantly
2. Verify match scores are showing correctly
3. Check that jobs are relevant to your CV
4. Let the scheduler run daily to keep recommendations fresh
5. Monitor logs for recommendation generation at 7 AM UTC

**Questions?** Check the logs or run the verification SQL queries above.
