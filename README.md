# AI-Powered Job Hunt Pro

A production-ready SaaS platform that uses AI to match users with jobs and generate tailored application materials with automated job scraping and intelligent recommendations.

## 🚀 Features

- **Advanced User Profiles**: Comprehensive career targeting, skills, experience, and preferences
- **AI Job Matching**: OpenAI embeddings-based matching with title boosting for 90%+ accuracy
- **Automated Job Scraping**: Daily scraping at 6 AM UTC from 3 free sources (Remotive, RemoteOK, Adzuna)
- **100+ Tech Keywords**: Comprehensive coverage of Software Engineering, Data Science, DevOps, Design, and more
- **Smart Deduplication**: Zero duplicate jobs in database
- **Two-Tab Interface**: Separate AI recommendations and filtered job search
- **Multi-Provider AI**: Supports OpenAI, Grok, Gemini, and Groq with intelligent routing
- **Secure & Scalable**: Built with Supabase Auth, RLS, and modern best practices

## 🛠️ Tech Stack

- **Frontend**: Next.js 14+ (App Router), React, TypeScript, Tailwind CSS
- **Backend**: Python FastAPI, SQLAlchemy, APScheduler
- **Database**: Supabase PostgreSQL with Row Level Security
- **Auth**: Supabase Auth (Email + OAuth)
- **Storage**: Supabase Storage
- **Job Scraping**: APScheduler (daily at 6 AM UTC)
- **AI Providers**: OpenAI, Grok, Gemini, Groq

## 📁 Project Structure

```
AI-Powered-JobHunt-Pro/
├── frontend/              # Next.js application
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── scheduler/   # APScheduler for automated job scraping
│   │   ├── scrapers/    # Job board scrapers (Remotive, RemoteOK, Adzuna)
│   │   └── services/    # AI matching, job scraping services
├── docs/                 # Documentation
│   ├── SUPABASE_SETUP_COMPLETE.sql  # Complete database setup
│   ├── JOB_SCHEDULER_SETUP.md       # Scheduler documentation
│   ├── TECH_JOB_SCRAPING_COMPLETE.md # Scraping guide
│   └── SCHEDULER_MIGRATION_COMPLETE.md # Migration summary
└── README.md            # This file
```

## 🚦 Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Supabase account
- OpenAI API key (for job matching)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd AI-Powered-JobHunt-Pro
   ```

2. **Set up Supabase**
   - Create a Supabase project
   - Run [docs/SUPABASE_SETUP_COMPLETE.sql](docs/SUPABASE_SETUP_COMPLETE.sql) in SQL Editor
   - Create a 'cvs' storage bucket

3. **Configure Backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your Supabase and OpenAI keys
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Configure Frontend**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with your Supabase credentials
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api/docs

### Documentation

- **Setup**: [docs/SETUP.md](docs/SETUP.md) - Detailed setup instructions
- **Database**: [docs/SUPABASE_SETUP_COMPLETE.sql](docs/SUPABASE_SETUP_COMPLETE.sql) - Complete database schema
- **Job Scraping**: [docs/JOB_SCHEDULER_SETUP.md](docs/JOB_SCHEDULER_SETUP.md) - Automated scraping setup
- **Project Plan**: [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) - Development roadmap

### Troubleshooting

Encountering errors? Check our guides:
- [Errors and Solutions](docs/ERRORS_AND_SOLUTIONS.md) - Complete error catalog
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues and fixes

## 📊 Key Features Explained

### Automated Job Scraping
- **Schedule**: Daily at 6:00 AM UTC
- **Sources**: Remotive, RemoteOK, Adzuna (all FREE)
- **Keywords**: 100+ tech job categories
- **Freshness**: Only jobs posted within last 2 days
- **Deduplication**: Automatic prevention of duplicate entries

See [docs/JOB_SCHEDULER_SETUP.md](docs/JOB_SCHEDULER_SETUP.md) for details.

### AI Job Matching
- **Technology**: OpenAI embeddings (text-embedding-3-small)
- **Title Boosting**: +40% for exact matches, +30% for partial matches
- **Minimum Score**: 20% similarity threshold
- **Cache**: 1-hour cache for performance
- **Result**: 90%+ match accuracy for exact title matches

### Two-Tab Job Interface
- **Recommended for You**: AI-powered recommendations based on profile
- **All Jobs**: Filtered search by title, location, company, etc.
- **Smart Design**: Only shows filters in "All Jobs" tab

## 📝 Development Status

### ✅ Completed Features

- User authentication and profiles
- CV upload and management
- Automated job scraping (APScheduler)
- AI job matching with OpenAI embeddings
- Two-tab job search interface
- Smart deduplication
- Title boosting for exact matches
- 100+ tech job keywords

### 🎯 Roadmap

- AI-generated cover letters
- Tailored CV generation
- Application tracking
- Email templates
- Analytics dashboard

## 🎨 Design System

- **Primary**: Deep Purple (#6B46C1)
- **Secondary**: Coral Pink (#F472B6)
- **Accent**: Teal (#14B8A6)
- **Neutral**: Slate (#1E293B)

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

