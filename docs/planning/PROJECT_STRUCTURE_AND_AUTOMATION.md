# Project Structure & Automation Guide

## 📁 Organized Project Structure

```
AI-Powered-JobHunt-Pro/
├── backend/
│   ├── app/
│   │   ├── ai/                 # AI providers (OpenAI, Grok, Gemini)
│   │   ├── api/                # API endpoints
│   │   ├── core/               # Core configs (database, logging, settings)
│   │   ├── exceptions/         # Custom exceptions
│   │   ├── middleware/         # Error handling, request logging
│   │   ├── models/             # Database models (Job, User, CV, etc.)
│   │   ├── scrapers/           # Job board scrapers (RemoteOK, SerpAPI, etc.)
│   │   ├── services/           # Business logic
│   │   │   ├── ai_job_matcher.py          # 🤖 AI-powered job matching
│   │   │   ├── job_matching_service.py    # Original keyword matching
│   │   │   └── job_matching_service_optimized.py  # Optimized keyword matching
│   │   └── tasks/              # Background tasks (Celery)
│   ├── scripts/                # 📜 All scripts belong here
│   │   ├── cleanup_old_jobs.py           # Archive/delete old jobs
│   │   ├── daily_job_scraper.py          # Daily automated job scraping
│   │   ├── setup_cron_jobs.sh            # Setup automation (cron)
│   │   ├── seed_jobs.py                  # Original seeding script
│   │   ├── seed_jobs_remoteok.py         # RemoteOK seeding
│   │   ├── seed_jobs_improved.py         # Multi-query seeding
│   │   └── seed_jobs_simple.py           # Simple seeding
│   ├── tests/                  # Test files
│   ├── .env                    # Environment variables
│   ├── requirements.txt        # Python dependencies
│   └── main.py                 # FastAPI entry point
│
├── frontend/                   # Next.js frontend
│   ├── app/                    # Next.js 13+ app router
│   ├── components/             # React components
│   ├── lib/                    # Utilities and API clients
│   └── ...
│
└── docs/                       # 📚 All documentation belongs here
    ├── AI_MATCHING_UPGRADE.md               # AI matching implementation
    ├── JOB_MATCHING_FIX.md                  # Job matching fixes
    ├── SEEDING_GUIDE.md                     # Job seeding guide
    ├── TESTING_QUICKSTART.md                # Testing guide
    ├── FRONTEND_BACKEND_DIAGNOSTICS.md      # Connection diagnostics
    ├── TESTING_SETUP_SUMMARY.md             # Testing setup
    ├── MULTI_TITLE_FEATURE.md               # Multi-title job search feature
    ├── PROFILE_SIMPLIFICATION.md            # Profile wizard simplification (6→5 steps)
    └── PROJECT_STRUCTURE_AND_AUTOMATION.md  # This file
```

## 🤖 AI-Powered Job Matching

### What It Does
Matches jobs to user profiles using **OpenAI embeddings** (semantic similarity), not just keyword matching.

### Location
- Service: `backend/app/services/ai_job_matcher.py`
- Used in: `backend/app/api/v1/endpoints/jobs.py`

### How It Works
1. Creates AI embedding of user profile (skills, experience, goals)
2. Creates AI embedding of each job (title, description)
3. Calculates similarity score (0-100%)
4. Shows only 50%+ matches (motivating quality)

### Performance
- First search: 3-5 seconds
- Cached: <100ms
- Cost: ~$0.0004 per search

## 📅 Automated Job Management

### 1. Daily Job Scraping
**Script**: `scripts/daily_job_scraper.py`

**What it does**:
- Scrapes RemoteOK (free, no API key)
- Scrapes SerpAPI (requires `SERPAPI_API_KEY` in `.env`)
- Removes duplicates
- Adds ~50-100 new jobs daily

**Run manually**:
```bash
cd backend
python scripts/daily_job_scraper.py
```

### 2. Database Cleanup (Application-Aware)
**Script**: `scripts/cleanup_old_jobs.py`

**What it does**:
- **KEEPS** jobs that users have applied to (forever - for tracking)
- **DELETES** jobs older than 7 days with NO applications
- Cleans old job match cache (90+ days)

**Run manually**:
```bash
cd backend
python scripts/cleanup_old_jobs.py
```

**Why this strategy?**
- ✅ Users can track their application history forever
- ✅ Database stays lean (removes jobs nobody cared about)
- ✅ Never loses jobs users actually applied to

### 3. Setup Automation (Cron)
**Script**: `scripts/setup_cron_jobs.sh`

**What it does**:
- Sets up daily cron jobs for scraping (2 AM) and cleanup (3 AM)
- Creates log files in `backend/logs/`

**Setup**:
```bash
cd backend
chmod +x scripts/setup_cron_jobs.sh
./scripts/setup_cron_jobs.sh
```

**View scheduled jobs**:
```bash
crontab -l
```

**View logs**:
```bash
tail -f logs/job_scraper.log
tail -f logs/job_cleanup.log
```

## 🔧 Database Management Strategy (Application-Aware)

### Job Lifecycle

**For jobs WITH applications** (user applied):
```
Day 0:   Job scraped
Day 1:   User applies to job → Application created
Day 7+:  Job KEPT forever (for user's application tracking)
```

**For jobs WITHOUT applications** (user didn't care):
```
Day 0:  Job scraped → status: "pending"
Day 1:  Matched to user → Cached in job_matches
Day 7:  No applications → DELETED from database
```

### Why Application-Aware Cleanup?

**Jobs WITH applications:**
- ✅ Kept **forever** so users can track their applications
- ✅ Preserves application history
- ✅ Users can reference job details months later

**Jobs WITHOUT applications:**
- ✅ Deleted after 7 days (nobody cared about them)
- ✅ Keeps database lean and fast
- ✅ Removes noise from job searches

### Database Tables
- `jobs` - Job postings (kept if has applications, deleted after 7 days if not)
- `applications` - User's job applications (kept forever)
- `job_matches` - Cached AI match results (cleaned after 90 days)
- User sees only jobs with 50%+ match scores

## 🚀 Quick Start

### Initial Setup
```bash
# 1. Seed some jobs
cd backend
python scripts/seed_jobs_remoteok.py

# 2. Setup automated scraping
./scripts/setup_cron_jobs.sh

# 3. Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### User searches for jobs
1. Frontend calls `/api/v1/jobs/?matched=true`
2. Backend uses AI matcher (50%+ threshold)
3. Returns cached matches if available (<1 hour old)
4. Otherwise computes new matches using OpenAI embeddings
5. Caches results for 1 hour

## 📊 Monitoring

### Check Database Stats
```bash
cd backend
python scripts/cleanup_old_jobs.py  # Shows stats at end
```

### Check API Logs
```bash
# Backend logs
tail -f backend.log | grep "AI"

# Scraping logs
tail -f logs/job_scraper.log

# Cleanup logs
tail -f logs/job_cleanup.log
```

### Check Cron Jobs
```bash
crontab -l
```

## 🔑 Environment Variables

Required in `backend/.env`:
```bash
# OpenAI (for AI job matching)
OPENAI_API_KEY=sk-proj-...

# SerpAPI (optional, for Google Jobs scraping)
SERPAPI_API_KEY=...

# Supabase (database)
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_KEY=...
SUPABASE_SERVICE_KEY=...
```

## 🎯 Key Features

### AI Job Matching
- ✅ 50%+ match scores (motivating quality)
- ✅ Understands synonyms and context
- ✅ Fast with 1-hour caching
- ✅ Cost-effective (~$0.0004/search)

### Automated Job Scraping
- ✅ Daily scraping from RemoteOK + SerpAPI
- ✅ Duplicate detection
- ✅ Auto-cleanup of old jobs
- ✅ Logs all activity

### Database Management
- ✅ Smart archiving (not deletion)
- ✅ 7-day threshold for archiving
- ✅ 30-day threshold for deletion
- ✅ Keeps database lean and fast

## 📝 Next Steps

1. **Monitor costs**: Check OpenAI API usage dashboard
2. **Tune threshold**: Adjust MIN_SCORE in `ai_job_matcher.py` if needed
3. **Add more sources**: Extend `daily_job_scraper.py` with more job boards
4. **User feedback**: Let users mark jobs as "not relevant" to improve matching

## 🆘 Troubleshooting

### No jobs showing up?
```bash
# Check if jobs exist
cd backend
python scripts/seed_jobs_remoteok.py

# Check if AI matcher is working
tail -f backend.log | grep "AI"
```

### Cron not running?
```bash
# Check cron jobs
crontab -l

# Check logs
ls -la logs/
```

### High API costs?
- Reduce `MAX_JOBS_PER_REQUEST` in `ai_job_matcher.py`
- Increase `CACHE_EXPIRY_HOURS` to cache longer
- Use keyword matching instead of AI for some searches

---

**All code is now properly organized!** 🎉
- Scripts → `backend/scripts/`
- Docs → `docs/`
- Services → `backend/app/services/`
