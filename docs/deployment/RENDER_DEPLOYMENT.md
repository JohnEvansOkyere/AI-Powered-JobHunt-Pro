# Deploying to Render

This guide covers deploying the AI-Powered JobHunt Pro backend to Render.

## Prerequisites

- Render account
- GitHub repository connected to Render
- Supabase database set up
- Environment variables ready

---

## Deployment Strategy

**Use `requirements.txt`** - Render automatically detects and installs from this file.

Both files are maintained:
- **`requirements.txt`**: Used by Render for deployment (primary)
- **`pyproject.toml`**: Used for local development and modern Python tooling

---

## Step 1: Prepare Your Repository

Ensure these files are in your `backend/` directory:

```
backend/
├── requirements.txt          # ✅ Required for Render
├── pyproject.toml           # ✅ For local development
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── api/
│   ├── models/
│   ├── services/
│   └── ...
├── alembic/                 # Database migrations (if using)
└── .env.example             # Example environment variables
```

---

## Step 2: Render Configuration

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Note:** Render automatically provides the `$PORT` environment variable.

---

## Step 3: Environment Variables

Add these in Render's dashboard under "Environment":

### Required Variables

```bash
# Database (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
DATABASE_URL=postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI APIs
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
GROK_API_KEY=...

# Voice APIs (optional)
ELEVENLABS_API_KEY=...
DEEPGRAM_API_KEY=...

# Adzuna API (optional - for job scraping)
ADZUNA_APP_ID=your-app-id
ADZUNA_APP_KEY=your-app-key

# App Configuration
ENVIRONMENT=production
DEBUG=False
ALLOWED_ORIGINS=https://your-frontend.com,https://www.your-frontend.com
```

### Optional Variables

```bash
# Redis (if using Celery)
REDIS_URL=redis://...

# Sentry (error tracking)
SENTRY_DSN=...

# Custom Configuration
MAX_UPLOAD_SIZE=10485760  # 10MB
CV_STORAGE_PATH=/tmp/cvs
```

---

## Step 4: Python Version

Create a `runtime.txt` file in the `backend/` directory:

```bash
python-3.11.9
```

Or use Render's default Python 3.11+.

---

## Step 5: Health Check

Render will automatically ping your app. Ensure your FastAPI app has a health endpoint:

**File:** `app/main.py`

```python
@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
```

Render will use this to verify your app is running.

---

## Step 6: Database Migrations

### Option 1: Run Migrations on Build (Recommended)

Update your **Build Command**:

```bash
pip install -r requirements.txt && python -c "from app.core.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Option 2: Manual Migrations via Render Shell

After deployment:
1. Go to Render Dashboard → Your Service
2. Click "Shell" tab
3. Run:
   ```bash
   python -c "from app.core.database import Base, engine; Base.metadata.create_all(bind=engine)"
   ```

### Option 3: Alembic Migrations (Advanced)

If using Alembic, update build command:

```bash
pip install -r requirements.txt && alembic upgrade head
```

---

## Step 7: Supabase SQL Migrations

Run these in Supabase SQL Editor:

```bash
# 1. Create tables
migrations/001_initial_schema.sql
migrations/002_create_applications_table.sql
migrations/003_add_scraped_at_to_jobs.sql
migrations/004_create_job_recommendations.sql  # NEW
```

---

## Step 8: Scheduler Configuration

The scheduler starts automatically when your FastAPI app starts.

**Verify in logs:**
- Look for: `✅ Job scraper scheduler started successfully`
- Check schedule times:
  - Job Scraping: 6:00 AM UTC
  - Recommendations: 7:00 AM UTC
  - Cleanup: 12:00 AM UTC

**Important:** Ensure your Render plan supports **background workers**:
- Free tier: Workers sleep after inactivity
- Starter/Standard: Always-on workers (recommended)

---

## Step 9: Deploy

### Via Render Dashboard

1. Connect your GitHub repository
2. Select `backend` as root directory
3. Choose "Web Service"
4. Set build command, start command
5. Add environment variables
6. Click "Create Web Service"

### Via `render.yaml` (Infrastructure as Code)

Create `render.yaml` in your repo root:

```yaml
services:
  - type: web
    name: jobhunt-pro-backend
    env: python
    region: oregon
    plan: starter
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: OPENAI_API_KEY
        sync: false
      - key: ENVIRONMENT
        value: production
      - key: DEBUG
        value: False
```

Then:
```bash
render deploy
```

---

## Step 10: Verify Deployment

### Check Health Endpoint

```bash
curl https://your-app.onrender.com/health
```

Should return:
```json
{"status": "ok", "timestamp": "2026-01-10T17:00:00"}
```

### Check API Docs

Visit: `https://your-app.onrender.com/docs`

Should show FastAPI Swagger UI.

### Check Logs

In Render Dashboard → Logs, verify:
- ✅ App started
- ✅ Scheduler initialized
- ✅ Database connected
- ✅ No errors

---

## Troubleshooting

### Issue: Module Not Found

**Error:** `ModuleNotFoundError: No module named 'apscheduler'`

**Fix:** Ensure `requirements.txt` includes all dependencies:
```bash
apscheduler>=3.10.0
sqlalchemy>=2.0.0
```

### Issue: Database Connection Failed

**Error:** `could not connect to server`

**Fix:** Check `DATABASE_URL` format:
```
postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres
```

Remove any `?` query parameters from Supabase connection string.

### Issue: Port Already in Use

**Fix:** Use `$PORT` environment variable:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Issue: Scheduler Not Running

**Symptoms:** Jobs not being scraped at 6 AM

**Fix:**
1. Check logs for scheduler initialization
2. Verify Render plan supports always-on workers
3. Ensure app doesn't sleep (use cron-job.org to ping health endpoint)

### Issue: Import Errors

**Error:** `ImportError: cannot import name 'X' from 'Y'`

**Fix:** Check Python version matches requirements:
- Use Python 3.11+ (create `runtime.txt`)
- Update imports if using Python 3.13+

---

## Performance Tips

### 1. Use Render's Starter Plan

Free tier puts app to sleep after inactivity. Starter plan ($7/month) keeps it awake.

### 2. Enable Redis for Caching

Add Redis instance:
```yaml
- type: redis
  name: jobhunt-redis
  plan: starter
```

### 3. Monitor with Sentry

Add Sentry for error tracking:
```bash
pip install sentry-sdk[fastapi]
```

### 4. Use CDN for Static Assets

If serving files, use Render's CDN or external storage (S3, Supabase Storage).

---

## Scaling

### Horizontal Scaling

Render allows multiple instances:
```yaml
instances: 2  # Run 2 instances
```

### Vertical Scaling

Upgrade to higher plan:
- **Standard:** 2GB RAM, 1 CPU
- **Pro:** 4GB RAM, 2 CPU

### Database Scaling

Supabase handles scaling automatically. Monitor:
- Connection pool size
- Query performance
- Database size

---

## Cost Breakdown

| Service | Tier | Cost | Notes |
|---------|------|------|-------|
| Render Web Service | Starter | $7/mo | Always-on, 512MB RAM |
| Render Web Service | Standard | $25/mo | 2GB RAM |
| Supabase | Free | $0 | 500MB DB, 2GB bandwidth |
| Supabase | Pro | $25/mo | 8GB DB, 250GB bandwidth |
| **Total (Starter)** | | **$7-32/mo** | Depends on DB usage |

---

## Next Steps

1. ✅ Deploy backend to Render
2. ✅ Run Supabase migrations
3. ✅ Test API endpoints
4. ✅ Verify scheduler is running
5. Deploy frontend (Vercel/Netlify)
6. Connect frontend to backend
7. Monitor logs and errors
8. Set up alerts

---

## Support

- **Render Docs:** https://render.com/docs
- **Supabase Docs:** https://supabase.com/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com

---

**Your backend is production-ready!** 🚀

The system will automatically:
- Scrape jobs daily at 6 AM UTC
- Generate recommendations at 7 AM UTC
- Clean up old data at midnight UTC
- Handle all API requests
- Scale as needed
