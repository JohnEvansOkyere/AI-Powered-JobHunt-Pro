# Setup Guide

Complete setup instructions for the AI-Powered Job Application Platform.

## Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.11+
- Supabase account
- AI provider API keys (OpenAI, Grok/Gemini/Groq - at least one)

## 1. Supabase Setup

### Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your project URL and API keys:
   - Project URL
   - Anon/Public Key
   - Service Role Key

### Run Database Schema

1. Open Supabase SQL Editor
2. Copy and paste the contents of `docs/SUPABASE_SCHEMA.sql`
3. Execute the SQL script
4. Verify tables are created in the Table Editor

### Configure Storage

1. Go to Storage in Supabase dashboard
2. Create a bucket named `cvs` (or update `SUPABASE_STORAGE_BUCKET` in backend config)
3. Set bucket to **Private** (RLS enabled)
4. Add storage policy to allow users to upload their own files

## 2. Backend Setup

### Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure Environment

1. Copy `.env.example` to `.env` (if not blocked by gitignore)
2. Fill in all required values:

```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
SUPABASE_STORAGE_BUCKET=cvs

# Database (from Supabase project settings)
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres

# AI Providers (at least one required)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
GROK_API_KEY=...
GROQ_API_KEY=...

# Security
SECRET_KEY=generate_a_random_secret_key_here

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0
```

### Verify Database Schema

After running the SQL schema in Supabase, verify that all tables are created:
- Go to Supabase Dashboard → Table Editor
- You should see: `user_profiles`, `cvs`, `jobs`, `job_matches`, `applications`, `scraping_jobs`

### Future Schema Changes

For any future database schema changes:
1. Create a new SQL file in `docs/` (e.g., `docs/migrations/001_add_new_column.sql`)
2. Run the SQL in Supabase SQL Editor
3. Update your SQLAlchemy models in `backend/app/models/` to match
4. Commit both the SQL file and model changes to Git

### Start Backend Server

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python
python -m uvicorn app.main:app --reload
```

### Start Celery Worker (for background jobs)

```bash
# In a separate terminal
celery -A app.tasks.celery_app worker --loglevel=info
```

## 3. Frontend Setup

### Install Dependencies

```bash
cd frontend
npm install
# or
yarn install
```

### Configure Environment

Create `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Start Development Server

```bash
npm run dev
# or
yarn dev
```

Frontend will be available at `http://localhost:3000`

## 4. Verify Setup

1. **Backend Health Check**: Visit `http://localhost:8000/health`
2. **API Docs**: Visit `http://localhost:8000/api/docs` (if DEBUG=true)
3. **Frontend**: Visit `http://localhost:3000`

## 5. Next Steps

- Set up authentication (Phase 2)
- Configure user profiles (Phase 3)
- Upload and parse CVs (Phase 4)
- Test AI integrations (Phase 5)

## Troubleshooting

### Backend Issues

- **Import errors**: Ensure you're in the virtual environment
- **Database connection**: Verify DATABASE_URL is correct
- **Supabase errors**: Check API keys and project URL

### Frontend Issues

- **Supabase connection**: Verify environment variables
- **API errors**: Check backend is running and CORS is configured

### AI Provider Issues

- **API key errors**: Verify keys are correct and have credits
- **Rate limits**: Check provider rate limits and quotas

## Production Deployment

See `docs/DEPLOYMENT.md` for deployment instructions to Render (backend) and Vercel (frontend).

