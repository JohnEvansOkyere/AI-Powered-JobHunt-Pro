# Quick Start: Generate Recommendations Now

The recommendations database is currently empty. Here's the **fastest way** to populate it for testing:

## Option 1: API Call (Easiest - 30 seconds)

### In Browser Console (While logged into dashboard):

```javascript
fetch('/api/v1/jobs/recommendations/generate', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('access_token')
  }
})
.then(r => r.json())
.then(data => {
  console.log(data)
  alert(`✅ Generated ${data.recommendations_count} recommendations!`)
})
```

### Or Using curl:

```bash
curl -X POST http://localhost:8000/api/v1/jobs/recommendations/generate \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

---

## Option 2: Python Script (For All Users)

```bash
cd backend
python generate_recommendations.py
```

---

## Then Test It

1. Go to Jobs page
2. Click **"Recommended for You"** tab
3. Should load **instantly** with match scores!

---

## Full Documentation

For more options and troubleshooting, see:
- [GENERATE_INITIAL_RECOMMENDATIONS.md](GENERATE_INITIAL_RECOMMENDATIONS.md) - All methods
- [PRE_COMPUTED_RECOMMENDATIONS_IMPLEMENTATION.md](PRE_COMPUTED_RECOMMENDATIONS_IMPLEMENTATION.md) - Full implementation details

---

## What Happens Next

- **Daily at 7 AM UTC**: Scheduler automatically generates fresh recommendations
- **Expiry**: Recommendations expire after 3 days
- **No action needed**: System maintains itself automatically

---

**Need help?** Check the logs or verify:
1. You have a CV uploaded (Profile → Upload CV)
2. Jobs exist in database (run scraper if needed)
3. Backend is running with OpenAI API key configured
