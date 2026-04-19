# AI-Powered CV & Cover Letter Generator - Feature Documentation

## Overview

The AI-Powered CV & Cover Letter Generator allows users to instantly create tailored application materials by simply pasting a job posting link or description. The system uses advanced AI to analyze job requirements and customize CVs and cover letters to match specific positions.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Features](#features)
3. [How It Works](#how-it-works)
4. [Supported Job Boards](#supported-job-boards)
5. [User Guide](#user-guide)
6. [Technical Architecture](#technical-architecture)
7. [API Documentation](#api-documentation)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Quick Start

### For Users

1. **Upload Your CV** (one-time setup)
   - Go to CV Management
   - Upload your master CV (DOCX recommended)
   - Wait for parsing to complete

2. **Generate Application Materials**
   - Click "AI Generator (Paste Any Job)"
   - Choose input method:
     - **Easy**: Paste a job posting URL
     - **Manual**: Paste job description text
   - Click "Generate CV" or "Generate Letter"
   - Download/copy your materials

**That's it!** The entire process takes 30-60 seconds.

---

## Features

### 🔗 Job Link Scraping
- **Paste any job URL** - No more copying descriptions
- **Auto-extraction** - Title, company, location automatically extracted
- **Multi-platform support** - Works with LinkedIn, Indeed, Glassdoor, and more
- **Fallback handling** - Manual input if scraping fails

### 📄 CV Generation
- **Format preservation** - DOCX files keep original formatting
- **AI tailoring** - Highlights relevant experience and skills
- **Instant download** - Generated file ready immediately
- **Original unchanged** - Your master CV stays untouched

### ✉️ Cover Letter Generation
- **Professional formatting** - Proper business letter structure
- **Personalized content** - Specific to job and your experience
- **Multiple lengths** - Short (3¶), Medium (4¶), Long (5¶)
- **Copy-to-clipboard** - Easy to paste into applications

### 🎨 User Experience
- **Two-step process** - Paste → Generate
- **Clear feedback** - Progress indicators and error messages
- **Professional design** - Clean, modern interface
- **Mobile responsive** - Works on all devices

---

## How It Works

### Process Flow

```
┌─────────────────┐
│ User Input      │
│ (Link or Text)  │
└────────┬────────┘
         │
         ├─ Job Link? ──Yes──→ ┌──────────────┐
         │                      │ Web Scraper  │
         │                      │ Extracts JD  │
         │                      └──────┬───────┘
         │                             │
         └─ Description? ──Yes──→ ─────┤
                                       │
                              ┌────────▼────────┐
                              │ AI Processing   │
                              │ - Analyzes JD   │
                              │ - Reads CV      │
                              │ - Tailors       │
                              └────────┬────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      │                                  │
              ┌───────▼────────┐              ┌────────▼──────────┐
              │ CV Generation  │              │ Cover Letter Gen  │
              │ - DOCX format  │              │ - Text format     │
              │ - Downloadable │              │ - Copyable        │
              └────────────────┘              └───────────────────┘
```

### Detailed Steps

#### 1. Job Information Extraction

**Option A: Job Link (Recommended)**
```
Input: https://linkedin.com/jobs/view/123456789
  ↓
URL Validation → Web Scraping → HTML Parsing → Data Extraction
  ↓
Output: {
  title: "Senior Software Engineer",
  company: "Tech Corp",
  location: "San Francisco, CA",
  description: "Full job description text..."
}
```

**Option B: Manual Description**
```
Input: User pastes job description + provides title & company
  ↓
No scraping needed, direct processing
  ↓
Output: Same format as Option A
```

#### 2. AI Analysis

The AI analyzes:
- **Job Requirements**: Skills, experience level, responsibilities
- **Company Context**: Industry, size, culture indicators
- **Your CV**: Experience, skills, projects, education
- **Best Matches**: Which parts of your background align best

#### 3. Content Generation

**For CVs:**
- Reorders skills to put relevant ones first
- Rewrites experience bullets to emphasize relevant achievements
- Adjusts professional summary for the specific role
- Maintains ALL original content (nothing removed)
- Preserves your CV's formatting (if DOCX)

**For Cover Letters:**
- Professional business letter format
- Personalized opening addressing the role
- 2-3 body paragraphs with specific examples
- Enthusiastic closing with call to action
- Proper sign-off

#### 4. Delivery

- **CV**: Uploaded to secure storage, download link provided
- **Cover Letter**: Displayed in-app with copy button
- **Application Record**: Saved to your account for tracking

---

## Supported Job Boards

### ✅ Fully Supported (Optimized Scraping)

| Job Board | Status | Auto-Extract | Notes |
|-----------|--------|--------------|-------|
| **LinkedIn** | ✅ Full | Title, Company, Location, Description | Best results |
| **Indeed** | ✅ Full | Title, Company, Location, Description | Excellent |
| **Glassdoor** | ✅ Full | Title, Company, Location, Description | Good |
| **Greenhouse** | ✅ Full | Title, Description, Location | ATS platform |
| **Lever** | ✅ Full | Title, Description, Location | ATS platform |
| **Generic Sites** | ⚠️ Partial | Description only | Fallback scraper |

### 📝 Manual Input Always Available

If scraping fails or you prefer manual input:
- Switch to "Paste Description" tab
- Provide job title and company manually
- Paste job description
- System works identically

---

## User Guide

### Getting Started

#### Step 1: Prepare Your Master CV

**Best Practices:**
- Use DOCX format (not PDF) for best formatting preservation
- Include complete work history, skills, education
- Use clear section headers
- Include quantifiable achievements
- Keep formatting professional but simple

**Upload Process:**
1. Navigate to CV Management
2. Drag & drop or click to upload
3. Wait for "Parsing: Completed" status
4. Your CV is ready for tailoring!

#### Step 2: Find a Job Posting

**Supported Sources:**
- LinkedIn job postings
- Indeed listings
- Glassdoor job pages
- Company career pages (most)
- Any job board with public URLs

**Copy the Link:**
- Just copy the URL from your browser address bar
- No need to copy the description text
- Link can be from mobile or desktop site

#### Step 3: Generate Materials

**Using Job Links (Easiest):**

1. Click "AI Generator (Paste Any Job)" from CV Management
2. Select "Paste Job Link" tab (default)
3. Paste the URL in the input field
4. Click "Generate CV" or "Generate Letter"
5. Wait 15-30 seconds
6. Download CV or copy cover letter!

**Using Manual Description:**

1. Click "AI Generator (Paste Any Job)"
2. Select "Paste Description" tab
3. Fill in:
   - Job Title (required)
   - Company Name (required)
   - Job Description (required)
4. Click "Generate CV" or "Generate Letter"
5. Wait 15-30 seconds
6. Download CV or copy cover letter!

### Advanced Options

Click "▶ Advanced Options" to customize:

**Tone Options:**
- **Professional**: Formal, business-appropriate (default)
- **Confident**: Assertive, strong conviction
- **Friendly**: Warm, approachable
- **Enthusiastic**: Energetic, excited about opportunity

**Cover Letter Length:**
- **Short**: 3 paragraphs, ~250 words
- **Medium**: 4 paragraphs, ~350 words (default)
- **Long**: 5 paragraphs, ~450 words

**When to Use Each:**
- Short: Quick applications, competitive markets
- Medium: Standard applications (recommended)
- Long: Senior roles, detailed explanations needed

### Downloading & Using Materials

**CV Download:**
- Click "Download CV" button
- Opens in new tab for immediate download
- File name: `tailored_cv_[jobid]_[timestamp].docx`
- Save to appropriate folder for the application

**Cover Letter Copy:**
- Click "Copy to Clipboard" button
- Paste into application portal
- OR paste into email
- OR save to Word document for later

**Tips:**
- Review materials before submitting
- Minor edits are OK (fix typos, adjust wording)
- Keep formatting intact when copying
- Save both CV and cover letter together

---

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (Next.js)                 │
│  ┌──────────────┐         ┌────────────────────┐   │
│  │   UI Layer   │────────→│   API Client       │   │
│  │  (React)     │←────────│  (applications.ts) │   │
│  └──────────────┘         └────────────────────┘   │
└────────────────────┬────────────────────────────────┘
                     │ HTTPS/REST API
┌────────────────────▼────────────────────────────────┐
│                Backend (FastAPI)                     │
│  ┌──────────────────┐  ┌──────────────────────┐    │
│  │  API Endpoints   │  │   Job Scraper        │    │
│  │  applications.py │──│   job_scraper.py     │    │
│  └────────┬─────────┘  └──────────────────────┘    │
│           │                                          │
│  ┌────────▼──────────┐  ┌──────────────────────┐   │
│  │  CV Generator     │  │  Cover Letter Gen    │   │
│  │  cv_generator.py  │  │  cover_letter_gen.py │   │
│  └────────┬──────────┘  └──────────┬───────────┘   │
│           │                         │               │
│  ┌────────▼─────────────────────────▼───────────┐  │
│  │          AI Service (OpenAI/etc)             │  │
│  │               ai_service.py                   │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         Database (PostgreSQL)                │  │
│  │    Storage (Supabase)                        │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Data Flow

#### CV Generation Flow

```
1. User submits request
   ↓
2. Backend validates input
   - URL format if job_link provided
   - Required fields if manual description
   ↓
3. Job scraping (if link provided)
   - HTTP request to job board
   - HTML parsing with BeautifulSoup
   - Data extraction (title, company, description)
   ↓
4. Create temporary job record
   - Store in database with source="custom"
   - Generate unique job ID
   ↓
5. Fetch user's active CV
   - Download from storage
   - Parse content (already done during upload)
   ↓
6. AI processing
   - Send CV data + job description to AI
   - AI analyzes and generates tailored content
   - Returns structured JSON
   ↓
7. CV file generation
   - Load original DOCX file
   - Update content while preserving formatting
   - Save as new file
   ↓
8. Upload to storage
   - Path: tailored-cvs/{user_id}/custom_{timestamp}_{filename}
   - Generate public URL
   ↓
9. Create application record
   - Link to job, CV, and generated file
   - Store generation settings
   ↓
10. Return response
    - application_id
    - cv_path
    - public_url
    - status: "completed"
```

#### Cover Letter Generation Flow

```
1-4. Same as CV generation
   ↓
5. Fetch user's active CV
   - Extract personal info (name, contact)
   - Get experience summary
   ↓
6. AI processing
   - Send CV summary + job description to AI
   - AI writes personalized cover letter
   - Returns formatted text
   ↓
7. Create application record
   - Store cover letter text in database
   - Link to job and CV
   ↓
8. Return response
    - application_id
    - cover_letter (full text)
    - status: "completed"
```

### Key Technologies

**Frontend:**
- Next.js 14 (React framework)
- TypeScript (type safety)
- Tailwind CSS (styling)
- React Hot Toast (notifications)
- Lucide Icons (UI icons)

**Backend:**
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- PostgreSQL (database)
- BeautifulSoup4 (web scraping)
- Requests (HTTP client)
- Supabase (file storage)

**AI:**
- OpenAI GPT (or other providers)
- AI Router (provider abstraction)
- Token usage tracking
- Rate limiting

---

## API Documentation

### Generate CV from Custom Job

**Endpoint:** `POST /api/v1/applications/generate-cv-custom`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "job_title": "Senior Software Engineer",      // Optional if job_link provided
  "company_name": "Tech Corp",                   // Optional if job_link provided
  "job_description": "Full text...",             // Optional, either this OR job_link
  "job_link": "https://linkedin.com/jobs/...",   // Optional, either this OR job_description
  "location": "San Francisco, CA",               // Optional
  "job_type": "full-time",                       // Optional: full-time, part-time, contract, internship
  "remote_type": "hybrid",                       // Optional: remote, hybrid, on-site, unspecified
  "tone": "professional",                        // Optional: professional, confident, friendly, enthusiastic
  "highlight_skills": true,                      // Optional, default: true
  "emphasize_relevant_experience": true          // Optional, default: true
}
```

**Response (200 OK):**
```json
{
  "application_id": "uuid-string",
  "cv_path": "tailored-cvs/user123/custom_20240115_123456_cv.docx",
  "public_url": "https://storage.supabase.co/...",
  "status": "completed",
  "created_at": "2024-01-15T12:34:56Z"
}
```

**Error Responses:**

```json
// 400 Bad Request - Validation error
{
  "detail": "Either job_description or job_link must be provided"
}

// 400 Bad Request - Scraping error
{
  "detail": "Job posting not found (404). The link might be expired or invalid."
}

// 400 Bad Request - No CV
{
  "detail": "No active CV found. Please upload a CV first."
}

// 500 Internal Server Error - Generation error
{
  "detail": "Failed to generate tailored CV: [error message]"
}
```

### Generate Cover Letter from Custom Job

**Endpoint:** `POST /api/v1/applications/generate-cover-letter-custom`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "job_title": "Senior Software Engineer",      // Optional if job_link provided
  "company_name": "Tech Corp",                   // Optional if job_link provided
  "job_description": "Full text...",             // Optional, either this OR job_link
  "job_link": "https://linkedin.com/jobs/...",   // Optional, either this OR job_description
  "location": "San Francisco, CA",               // Optional
  "job_type": "full-time",                       // Optional
  "remote_type": "hybrid",                       // Optional
  "tone": "professional",                        // Optional: professional, confident, friendly, enthusiastic
  "length": "medium"                             // Optional: short, medium, long
}
```

**Response (200 OK):**
```json
{
  "application_id": "uuid-string",
  "cover_letter": "[Date]\n\nHiring Manager\nTech Corp\n\nDear Hiring Manager,\n\n...",
  "status": "completed",
  "created_at": "2024-01-15T12:34:56Z"
}
```

**Error Responses:** Same as CV generation endpoint

---

## Troubleshooting

### Common Issues & Solutions

#### Issue: "Job posting not found (404)"

**Cause:** The job link is expired or removed

**Solutions:**
1. Check if the job is still live on the website
2. Try refreshing the job page
3. If expired, switch to "Paste Description" and copy manually
4. Some jobs are removed quickly - this is normal

#### Issue: "Access denied (403)"

**Cause:** Website is blocking automated access

**Solutions:**
1. Switch to "Paste Description" tab
2. Manually copy the job description
3. Paste and continue normally
4. This happens with some career pages - manual input works fine

#### Issue: "Request timed out"

**Cause:** Job board website is slow or down

**Solutions:**
1. Try again in a few minutes
2. Check if website is accessible in browser
3. Use manual description input as alternative
4. Report persistent issues to support

#### Issue: "No active CV found"

**Cause:** You haven't uploaded a CV yet

**Solutions:**
1. Go to CV Management
2. Upload your CV (DOCX recommended)
3. Wait for parsing to complete
4. Return to AI Generator

#### Issue: "CV has not been parsed yet"

**Cause:** Upload is processing

**Solutions:**
1. Wait 30-60 seconds
2. Refresh the page
3. Check CV Management for parsing status
4. If stuck on "processing" for >5 minutes, delete and re-upload

#### Issue: "Could not extract job description"

**Cause:** Unknown job board format

**Solutions:**
1. Switch to "Paste Description" tab
2. Copy job description from website
3. Paste into form with title and company
4. System will work identically

#### Issue: Generated CV doesn't preserve formatting

**Cause:** Original CV was PDF format

**Solutions:**
1. Upload DOCX version of your CV
2. PDF files can't be edited, so new format is created
3. DOCX files preserve your original formatting perfectly

### Getting Help

**Documentation:**
- Read this full guide
- Check [ERROR_HANDLING_GUIDE.md](../../troubleshooting/ERROR_HANDLING_GUIDE.md)
- Review [TROUBLESHOOTING.md](../../troubleshooting/TROUBLESHOOTING.md)

**Support Channels:**
- Check browser console for detailed errors
- Review backend logs (if you have access)
- Contact support with:
  - Error message
  - Job board URL (if applicable)
  - Steps to reproduce

---

## Best Practices

### For Best Results

**CV Preparation:**
1. ✅ Use DOCX format (not PDF)
2. ✅ Include complete work history
3. ✅ Use quantifiable achievements (numbers, percentages)
4. ✅ Keep formatting simple and professional
5. ✅ Include all relevant skills
6. ❌ Don't use complex templates
7. ❌ Don't use images or graphics
8. ❌ Don't omit important experience

**Job Link Usage:**
1. ✅ Use direct job posting URLs
2. ✅ Copy full URL from browser
3. ✅ Test link in browser first
4. ✅ Use fresh, recent postings
5. ❌ Don't use search result URLs
6. ❌ Don't use shortened links
7. ❌ Don't use expired postings

**Manual Description:**
1. ✅ Copy complete job description
2. ✅ Include requirements and responsibilities
3. ✅ Provide accurate job title
4. ✅ Use exact company name
5. ❌ Don't abbreviate or summarize
6. ❌ Don't skip important sections
7. ❌ Don't paste only requirements

**Tone Selection:**
- **Startups, Tech**: Confident or Friendly
- **Corporate, Finance**: Professional
- **Creative, Marketing**: Enthusiastic or Friendly
- **Government, Academia**: Professional
- **When unsure**: Professional (always safe)

**Cover Letter Length:**
- **Quick Apply**: Short
- **Standard Application**: Medium
- **Senior/Executive**: Long
- **Highly Competitive**: Long
- **Casual Company**: Short or Medium

**Review Before Submitting:**
1. ✅ Read generated CV for accuracy
2. ✅ Check cover letter for tone appropriateness
3. ✅ Verify company name spelling
4. ✅ Ensure job title is correct
5. ✅ Look for any AI hallucinations
6. ✅ Make minor edits if needed

**Application Strategy:**
1. Generate materials for each job individually
2. Don't reuse tailored CVs across different positions
3. Save both CV and cover letter together
4. Name files clearly: `CV_CompanyName_JobTitle.docx`
5. Keep track of which version you sent where
6. Update master CV periodically

---

## Security & Privacy

### Data Protection

**Your CV:**
- Stored securely in Supabase Storage
- Encrypted in transit and at rest
- Access controlled by authentication
- Only you can view/download your CVs

**Job Data:**
- Temporary job records created for tracking
- Marked as `source: "custom"`
- Not shared with other users
- Can be deleted from applications page

**AI Processing:**
- Data sanitized before sending to AI
- Sensitive information filtered
- No data retention by AI providers
- Logs contain no personal information

### Best Practices

**Protect Your Privacy:**
- Don't share your download links
- Log out on shared computers
- Use strong passwords
- Enable 2FA if available

**Data Management:**
- Delete old application records regularly
- Update your CV when experience changes
- Remove outdated tailored CVs
- Keep master CV current

---

## Performance & Limits

### Processing Times

| Operation | Typical Time | Max Time |
|-----------|--------------|----------|
| Job scraping | 2-5 seconds | 15 seconds |
| CV generation | 15-30 seconds | 60 seconds |
| Cover letter generation | 10-20 seconds | 45 seconds |
| CV parsing (upload) | 30-60 seconds | 2 minutes |

### Rate Limits

- **10 generations per hour** (combined CV + cover letter)
- **100 generations per day**
- **1,000 generations per month**

**If you hit limits:**
- Wait for the hour/day to reset
- Contact support for higher limits
- Review your usage patterns

### File Size Limits

- **CV upload**: Max 10MB
- **Job description**: Max 50,000 characters
- **Generated CV**: Typically 200-500KB
- **Cover letter**: Typically 2-5KB text

---

## FAQ

**Q: Can I use this for multiple job applications?**
A: Yes! Generate new materials for each job. Don't reuse tailored CVs.

**Q: Will my original CV be changed?**
A: No! Your master CV stays untouched. We create new versions.

**Q: What if the job link doesn't work?**
A: Switch to "Paste Description" tab and enter manually.

**Q: Can I edit the generated CV?**
A: Yes, download and edit in Word/Google Docs as needed.

**Q: Do I need to provide job title if using a link?**
A: No, we extract it automatically. But you can override if needed.

**Q: How accurate is the AI?**
A: Very high accuracy. Always review before submitting though.

**Q: Can I generate both CV and cover letter?**
A: Yes! Use the same job input, click both buttons.

**Q: What format is the CV?**
A: DOCX (Microsoft Word) format, compatible with all systems.

**Q: Can I download the cover letter?**
A: Use "Copy to Clipboard" then paste into Word/Docs and save.

**Q: Is my data secure?**
A: Yes, encrypted storage, secure processing, no data sharing.

**Q: What job boards are supported?**
A: LinkedIn, Indeed, Glassdoor, Greenhouse, Lever, and most others.

**Q: What if AI makes a mistake?**
A: Review and edit as needed. Report issues to support.

**Q: Can I customize the AI tone?**
A: Yes, in Advanced Options. Choose Professional/Confident/Friendly/Enthusiastic.

**Q: How long are generated CVs stored?**
A: Indefinitely, or until you delete them.

**Q: Can I share my generated materials?**
A: Yes, they're yours to use however you want!

---

## Version History

### v2.0.0 (January 2024)
- ✨ Added job link scraping support
- ✨ Complete UI/UX redesign
- ✨ Cover letter generation
- ✨ Advanced options collapse
- ✨ Support for 6+ job boards
- 🔧 Improved error handling
- 🔧 Better validation
- 🔧 Professional design
- 🔧 Mobile responsive

### v1.0.0 (December 2023)
- 🎉 Initial release
- ✨ CV generation from job descriptions
- ✨ Basic UI
- ✨ Manual input only

---

## Support & Feedback

**Need Help?**
- Email: support@yourcompany.com
- Docs: https://docs.yourcompany.com
- Status: https://status.yourcompany.com

**Report Issues:**
- Include error message
- Steps to reproduce
- Browser/device info
- Screenshots if helpful

**Feature Requests:**
- Submit via feedback form
- Vote on existing requests
- Join beta programs

**Stay Updated:**
- Follow changelog
- Subscribe to updates
- Join community forum

---

## Credits

**Built With:**
- OpenAI GPT (AI generation)
- BeautifulSoup (web scraping)
- FastAPI (backend)
- Next.js (frontend)
- Supabase (storage)
- PostgreSQL (database)

**Special Thanks:**
- Our amazing users for feedback
- Open source community
- Beta testers

---

*Last Updated: January 2024*
*Version: 2.0.0*
