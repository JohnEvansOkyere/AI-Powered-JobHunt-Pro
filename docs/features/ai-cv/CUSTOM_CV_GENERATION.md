# AI-Powered CV & Cover Letter Generator - Quick Reference

## What's New in v2.0

### 🔗 Job Link Support
- **Paste job links** instead of copying descriptions!
- Automatic extraction of job title, company, location, description
- Supports LinkedIn, Indeed, Glassdoor, and most job boards

### ✨ Professional UI Redesign
- Clean, modern interface
- Two-tab design: "Paste Job Link" or "Paste Description"
- Collapsible advanced options
- Clear success states

### ✉️ Cover Letter Generation
- Generate personalized cover letters
- Professional business letter format
- Three length options: Short, Medium, Long
- Copy-to-clipboard functionality

## Quick Start

### 1. Upload Your CV (One-Time)
```
Dashboard → CV Management → Upload CV (DOCX recommended)
```

### 2. Generate Materials
```
CV Management → "AI Generator (Paste Any Job)"
→ Paste job link OR description
→ Click "Generate CV" or "Generate Letter"
→ Download/Copy your materials
```

**Done in 30-60 seconds!**

## Features Overview

| Feature | Description |
|---------|-------------|
| **Job Link Scraping** | Paste LinkedIn, Indeed, Glassdoor links - auto-extracts details |
| **Manual Description** | Paste job description + provide title & company |
| **CV Generation** | Tailored DOCX file, preserves original formatting |
| **Cover Letter** | Professional letter with customizable tone & length |
| **Smart Fallback** | If link scraping fails, manual input always works |
| **Error Handling** | Clear, actionable error messages |

## Supported Job Boards

✅ **Fully Supported (Auto-Extract Everything):**
- LinkedIn
- Indeed
- Glassdoor
- Greenhouse (ATS)
- Lever (ATS)

⚠️ **Partial Support (Description Only):**
- Most other job boards

✅ **Always Available:**
- Manual description input

## Input Options

### Option 1: Job Link (Easiest)
```
Input: https://linkedin.com/jobs/view/123456789
↓
Auto-extracted:
- Job Title: "Senior Software Engineer"
- Company: "Tech Corp"  
- Location: "San Francisco, CA"
- Description: [Full text]
```

### Option 2: Manual Description
```
Input: 
- Job Title: [User types]
- Company: [User types]
- Description: [User pastes]
↓
Same as Option 1
```

## Customization Options

### Tone
- **Professional**: Formal, business-appropriate (default)
- **Confident**: Assertive, strong
- **Friendly**: Warm, approachable
- **Enthusiastic**: Energetic, excited

### Cover Letter Length
- **Short**: 3 paragraphs, ~250 words
- **Medium**: 4 paragraphs, ~350 words (default)
- **Long**: 5 paragraphs, ~450 words

## Technical Details

### Backend Stack
- **FastAPI**: API framework
- **BeautifulSoup**: Web scraping
- **PostgreSQL**: Database
- **Supabase**: File storage
- **OpenAI**: AI generation

### Frontend Stack
- **Next.js 14**: React framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling

### API Endpoints

**Generate CV:**
```
POST /api/v1/applications/generate-cv-custom
Body: {
  job_link: string (optional),
  job_description: string (optional),
  job_title: string,
  company_name: string,
  tone: string,
  ...
}
```

**Generate Cover Letter:**
```
POST /api/v1/applications/generate-cover-letter-custom
Body: {
  job_link: string (optional),
  job_description: string (optional),
  job_title: string,
  company_name: string,
  tone: string,
  length: string,
  ...
}
```

## Files Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/
│   │   └── applications.py          # Endpoints
│   ├── services/
│   │   ├── cv_generator.py          # CV generation
│   │   └── cover_letter_generator.py # Cover letter generation
│   └── utils/
│       └── job_scraper.py            # Web scraping

frontend/
├── app/dashboard/cv/
│   ├── page.tsx                      # CV management
│   └── custom/
│       └── page.tsx                  # Generator UI
└── lib/api/
    └── applications.ts               # API client
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Job posting not found (404)" | Expired link | Use manual description |
| "Access denied (403)" | Website blocking | Use manual description |
| "Request timed out" | Slow website | Try again or use manual |
| "No active CV found" | No CV uploaded | Upload CV first |
| "Could not extract job" | Unknown site | Use manual description |

## Performance

| Operation | Time |
|-----------|------|
| Job scraping | 2-5 seconds |
| CV generation | 15-30 seconds |
| Cover letter | 10-20 seconds |
| **Total** | **30-60 seconds** |

## Security

- ✅ URL validation before scraping
- ✅ 15-second timeout protection
- ✅ Input sanitization
- ✅ Encrypted storage
- ✅ Authentication required
- ✅ No data retention by AI

## Best Practices

### For Users
1. ✅ Use DOCX format for CV (not PDF)
2. ✅ Use fresh job posting links
3. ✅ Review generated materials
4. ✅ Generate separately for each job
5. ❌ Don't reuse tailored CVs

### For Developers
1. ✅ Add comprehensive tests
2. ✅ Monitor error rates
3. ✅ Log scraping failures
4. ✅ Implement rate limiting
5. ✅ Cache scraped data

## Rate Limits

- **10 generations/hour** per user
- **100 generations/day** per user
- **1,000 generations/month** per user

## Documentation

### User Documentation
- [Complete User Guide](./AI_CV_GENERATOR_USER_GUIDE.md) - Detailed usage instructions
- [FAQ](./AI_CV_GENERATOR_USER_GUIDE.md#faq) - Common questions
- [Troubleshooting](./AI_CV_GENERATOR_USER_GUIDE.md#troubleshooting) - Problem solving

### Technical Documentation
- [Technical Docs](./AI_CV_GENERATOR_TECHNICAL_DOCS.md) - Architecture & implementation
- [API Reference](./AI_CV_GENERATOR_TECHNICAL_DOCS.md#api-endpoints) - Endpoint details
- [Development Guide](./AI_CV_GENERATOR_TECHNICAL_DOCS.md#development-workflow) - Setup & testing

## Version History

### v2.0.0 (January 2024) - Major Update
- ✨ Added job link scraping
- ✨ Complete UI/UX redesign
- ✨ Cover letter generation
- ✨ Support for 6+ job boards
- 🔧 Improved error handling
- 🔧 Professional design
- 🔧 Mobile responsive

### v1.0.0 (December 2023)
- 🎉 Initial release
- ✨ CV generation
- ✨ Manual input only

## Dependencies

### New in v2.0
```
beautifulsoup4>=4.12.0  # Web scraping
```

### Existing
```
requests>=2.32.3        # HTTP client
fastapi                 # API framework
sqlalchemy              # ORM
supabase                # Storage
```

## Support

**Documentation:**
- User Guide: `AI_CV_GENERATOR_USER_GUIDE.md`
- Technical Docs: `AI_CV_GENERATOR_TECHNICAL_DOCS.md`

**Code:**
- Backend: `backend/app/api/v1/endpoints/applications.py`
- Frontend: `frontend/app/dashboard/cv/custom/page.tsx`

**Issues:**
- Check logs for errors
- Review error messages
- Test with manual input
- Contact support if needed

## Quick Links

- [User Guide](./AI_CV_GENERATOR_USER_GUIDE.md) - Complete usage instructions
- [Technical Docs](./AI_CV_GENERATOR_TECHNICAL_DOCS.md) - Developer documentation
- [API Reference](./AI_CV_GENERATOR_TECHNICAL_DOCS.md#api-documentation) - Endpoint specs
- [Troubleshooting](./AI_CV_GENERATOR_USER_GUIDE.md#troubleshooting) - Problem solving

---

*Last Updated: January 2024*
*Version: 2.0.0*
