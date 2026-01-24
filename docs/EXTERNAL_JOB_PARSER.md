# External Job Parser - Implementation Guide

## ✅ Feature Complete

The external job parser is fully implemented and working! Users can now manually add job postings from any website.

## 🎯 What This Feature Does

Allows users to add job postings from external sources (LinkedIn, company websites, etc.) that aren't automatically scraped by the system. Uses AI to intelligently parse and extract structured job data.

## 📋 Files Created/Modified

### Backend
- **`backend/app/services/external_job_parser.py`** - AI-powered parser service
- **`backend/app/api/v1/endpoints/external_jobs.py`** - API endpoints
- **`backend/app/models/job.py`** - Updated Job model with new fields
- **`backend/app/api/v1/router.py`** - Registered external jobs router

### Frontend
- **`frontend/components/modals/AddExternalJobModal.tsx`** - Modal component
- **`frontend/lib/api/external-jobs.ts`** - API client functions
- **`frontend/app/dashboard/page.tsx`** - Added "Add External Job" card

### Database
- **`migrations/005_add_external_jobs_support.sql`** - Migration to add new columns

## 🔥 New Database Fields

Added to `jobs` table:
- `source_url` - Original URL (for reference)
- `added_by_user_id` - User who added the job
- `salary_currency` - Currency code (USD, EUR, etc.)
- `remote_option` - Remote work availability
- `experience_level` - Entry/mid/senior/executive
- `requirements` - JSON array of requirements
- `responsibilities` - JSON array of responsibilities  
- `skills` - JSON array of required skills

## 🚀 How Users Access It

1. **Dashboard**: Prominent orange "Add External Job" card in the Quick Actions section
2. **Two Input Methods**:
   - **From URL**: Paste job URL (works with most public job boards)
   - **From Text**: Copy/paste job description (best for LinkedIn)

## ✅ Verified Working

**Test Case**: Wave Careers URL  
**URL**: `https://www.wave.com/en/careers/job/5724891004/?source=LinkedIn`

**Extracted Data**:
- ✅ Title: Machine Learning Scientist
- ✅ Company: Wave
- ✅ Location: Remote
- ✅ Salary: Up to $222,700 USD
- ✅ Job Type: Full-time
- ✅ Remote: Yes
- ✅ Experience: Mid-level
- ✅ Requirements: ["5 years of ML experience", "Strong proficiency in Python"...]
- ✅ Skills: ["Python", "GraphQL", "Kotlin", "Swift", "TypeScript"...]
- ✅ Responsibilities: ["Architect and ship autonomous voice agents"...]

## 🛡️ Smart Features

### 1. Login Detection
- Automatically detects when a URL requires authentication (like LinkedIn)
- Provides clear error message directing users to use "From Text" instead

### 2. Content Validation
- Checks for minimum content length (200+ chars)
- Validates extracted data has required fields

### 3. User Guidance
- Warning banner on "From URL" tab explaining LinkedIn limitation
- Helpful instructions on "From Text" tab showing how to copy job descriptions
- Example placeholder showing what good input looks like

## 📊 AI Parsing

Uses the application's AI router with:
- **Task Type**: `TaskType.JOB_ANALYSIS`
- **Model**: `gpt-4o-mini` (via OpenAI)
- **Temperature**: 0.1 (for consistent, factual extraction)
- **Max Tokens**: 2000

Extracts:
- Job title, company, location
- Salary range and currency
- Job type (full-time, part-time, contract)
- Remote work options
- Experience level
- Requirements, responsibilities, skills

## 🔒 Security

- User authentication required (uses `get_current_user` dependency)
- Jobs are linked to the user who added them (`added_by_user_id`)
- URL validation to prevent injection attacks
- Rate limiting via API timeout (30 seconds)

## 🎨 UI/UX Highlights

- **Orange gradient card** - Stands out on dashboard
- **Two-tab modal** - Clean switch between URL and Text input
- **Real-time feedback** - Loading states, success messages, error handling
- **Animations** - Smooth transitions with framer-motion
- **Icons** - Clear visual cues with lucide-react icons

## 📝 Usage Instructions

### For LinkedIn Jobs:
1. Open LinkedIn job in browser
2. Click "Add External Job" on dashboard
3. Switch to **"From Text"** tab
4. Press `Ctrl+A` to select all
5. Press `Ctrl+C` to copy
6. Paste into text box
7. Optionally add LinkedIn URL in "Source URL" field
8. Click "Add Job from Text"

### For Public Job Boards:
1. Copy the job URL
2. Click "Add External Job" on dashboard  
3. Use **"From URL"** tab
4. Paste URL
5. Click "Add Job from URL"

## 🐛 Known Limitations

1. **LinkedIn URLs** - LinkedIn requires login, so URLs won't work directly. Users must copy/paste the job description text instead.
2. **Heavy JavaScript Sites** - Some sites that render content client-side may not parse well. Text input is the fallback.
3. **Rate Limiting** - External sites may rate-limit our requests. Handled gracefully with error messages.

## 🔄 Database Migration

**Migration**: `005_add_external_jobs_support.sql`

Run with:
```bash
cd backend
python3 run_migration.py
```

**Status**: ✅ Successfully applied

## 📈 Next Steps (Future Enhancements)

- Add job preview before saving
- Support for bulk job imports
- Browser extension for one-click adding
- Job update/edit functionality
- Duplicate detection (same job from multiple sources)
