# AI CV & Cover Letter Generator - Technical Documentation

## Overview

This document provides technical details for developers working with the AI-powered CV and cover letter generation system.

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend Layer                          │
│  - Next.js 14 App Router                                    │
│  - TypeScript                                                │
│  - React Components                                          │
│  - API Client (fetch-based)                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ REST API (HTTPS)
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                     API Layer                                │
│  - FastAPI Framework                                         │
│  - Pydantic Models                                           │
│  - JWT Authentication                                        │
│  - Request Validation                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌─────────▼─────────┐
│ Job Scraper    │          │ Content Generators│
│ - BeautifulSoup│          │ - CV Generator    │
│ - Requests     │          │ - Letter Generator│
│ - HTML Parsing │          │ - AI Service      │
└───────┬────────┘          └─────────┬─────────┘
        │                             │
        └──────────────┬──────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌─────────▼─────────┐
│   Database     │          │   File Storage    │
│ - PostgreSQL   │          │ - Supabase        │
│ - SQLAlchemy   │          │ - DOCX files      │
└────────────────┘          └───────────────────┘
```

## Backend Implementation

### File Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── applications.py      # Main API endpoints
│   ├── services/
│   │   ├── cv_generator.py             # CV generation logic
│   │   └── cover_letter_generator.py   # Cover letter logic
│   ├── utils/
│   │   └── job_scraper.py              # Web scraping utility
│   └── models/
│       ├── application.py               # Application model
│       ├── job.py                       # Job model
│       └── cv.py                        # CV model
```

### Key Classes

#### JobDescriptionScraper

**Location:** `app/utils/job_scraper.py`

**Purpose:** Extract job information from URLs

**Methods:**

```python
def scrape_job_from_url(url: str) -> Dict[str, Any]:
    """
    Main entry point for scraping.
    
    Returns:
        {
            'title': str,
            'company': str,
            'location': str,
            'description': str,
            'source': str  # e.g., 'LinkedIn', 'Indeed'
        }
    
    Raises:
        ValueError: With user-friendly error message
    """
```

**Scraping Strategy:**

1. **Domain Detection**: Parse URL to identify job board
2. **Specialized Scrapers**: Use board-specific selectors
3. **Fallback**: Generic scraper for unknown sites
4. **Error Handling**: Clear messages for common failures

**Supported Selectors:**

```python
# LinkedIn
title: 'h1[class*="job.*title"]'
company: 'a[class*="topcard.*org"]'
description: 'div[class*="description"]'

# Indeed
title: 'h1[class*="JobInfoHeader"]'
company: 'div[class*="company"]'
description: 'div[id*="jobDescriptionText"]'

# Glassdoor
title: 'div[class*="job.*title"]'
company: 'div[class*="employer"]'
description: 'div[class*="job.*desc"]'

# Generic
title: 'h1' (first)
company: meta[property="og:site_name"]
description: 'main, article, [role="main"]'
```

**Error Handling:**

```python
# Timeout (15s)
→ "Request timed out. Website might be slow."

# 404 Not Found
→ "Job posting not found (404). Link might be expired."

# 403 Forbidden
→ "Access denied (403). Website blocking automated access."

# Connection Error
→ "Could not connect. Please check the URL."

# Parsing Error
→ "Could not extract job description from this website."
```

#### CVGenerator

**Location:** `app/services/cv_generator.py`

**Purpose:** Generate tailored CVs

**Key Method:**

```python
async def generate_tailored_cv_from_custom_description(
    user_id: str,
    job_title: str,
    company_name: str,
    job_description: str,
    location: Optional[str],
    job_type: Optional[str],
    remote_type: Optional[str],
    db: Session,
    tone: str = "professional",
    highlight_skills: bool = True,
    emphasize_relevant_experience: bool = True
) -> Dict[str, Any]:
    """
    Generate tailored CV from job details.
    
    Process:
    1. Validate user has active CV
    2. Create temporary job record
    3. Generate AI content
    4. Download original CV
    5. Create tailored version
    6. Upload to storage
    7. Create application record
    
    Returns:
        {
            'application_id': str,
            'cv_path': str,
            'public_url': str,
            'status': 'completed',
            'created_at': str
        }
    """
```

**AI Prompt Strategy:**

```python
# CRITICAL INSTRUCTIONS in prompt:
1. DO NOT REMOVE OR OMIT CONTENT
2. DO NOT FABRICATE information
3. REWRITE bullet points for relevance
4. KEEP ALL METRICS (90%, 5x, etc.)
5. KEEP ALL TECH STACK
6. REORDER for relevance
7. INCLUDE EVERYTHING

# Validation checklist:
✓ All work experience included?
✓ All projects included?
✓ All education included?
✓ All certifications included?
✓ All numbers preserved?
✓ All technology names preserved?
```

**File Handling:**

```python
# DOCX files:
- Load original document
- Update content preserving styles
- Save as new file

# PDF files:
- Create new DOCX (can't edit PDFs)
- Professional formatting
- All content from parsed data

# Storage:
Path: tailored-cvs/{user_id}/custom_{timestamp}_{filename}
Access: Public URL via Supabase
Retention: Indefinite (user can delete)
```

#### CoverLetterGenerator

**Location:** `app/services/cover_letter_generator.py`

**Purpose:** Generate personalized cover letters

**Key Method:**

```python
async def generate_cover_letter_from_custom_description(
    user_id: str,
    job_title: str,
    company_name: str,
    job_description: str,
    location: Optional[str],
    job_type: Optional[str],
    remote_type: Optional[str],
    db: Session,
    tone: str = "professional",
    length: str = "medium"
) -> Dict[str, Any]:
    """
    Generate personalized cover letter.
    
    Process:
    1. Validate user has active CV
    2. Create temporary job record
    3. Extract applicant info from CV
    4. Generate AI content
    5. Create application record
    
    Returns:
        {
            'application_id': str,
            'cover_letter': str,  # Full formatted text
            'status': 'completed',
            'created_at': str
        }
    """
```

**Letter Structure:**

```
[Date]

Hiring Manager
{company_name}

Dear Hiring Manager,

[Opening Paragraph]
- Reference specific position
- Show enthusiasm
- Brief intro of qualifications

[Body Paragraphs (1-3 based on length)]
- Relevant experience examples
- Specific achievements with metrics
- Skills matching job requirements
- Cultural fit indicators

[Closing Paragraph]
- Reiterate interest
- Call to action
- Thank you

Sincerely,
{applicant_name}
```

**Tone Implementation:**

```python
tone_instructions = {
    "professional": "Formal, courteous, business-like",
    "confident": "Assertive, strong conviction",
    "friendly": "Warm, approachable, professional",
    "enthusiastic": "Energetic, excited, positive"
}
```

### API Endpoints

#### POST /api/v1/applications/generate-cv-custom

**Request Validation:**

```python
class GenerateCustomCVRequest(BaseModel):
    job_title: str
    company_name: str
    job_description: Optional[str] = None
    job_link: Optional[str] = None  # Either this or description required
    location: Optional[str] = None
    job_type: Optional[str] = None
    remote_type: Optional[str] = None
    tone: Optional[str] = "professional"
    highlight_skills: bool = True
    emphasize_relevant_experience: bool = True
```

**Processing Flow:**

```python
async def generate_tailored_cv_custom(request, current_user, db):
    # 1. Validate input
    if not request.job_description and not request.job_link:
        raise HTTPException(400, "Either job_description or job_link required")
    
    # 2. Scrape if link provided
    if request.job_link:
        scraper = get_job_scraper()
        scraped_data = scraper.scrape_job_from_url(request.job_link)
        job_description = scraped_data['description']
        
        # Use scraped data to fill missing fields
        if not request.job_title:
            request.job_title = scraped_data.get('title')
        if not request.company_name:
            request.company_name = scraped_data.get('company')
    
    # 3. Generate CV
    cv_generator = get_cv_generator()
    result = await cv_generator.generate_tailored_cv_from_custom_description(
        user_id=str(current_user["id"]),
        job_title=request.job_title,
        company_name=request.company_name,
        job_description=job_description,
        ...
    )
    
    # 4. Return response
    return GenerateCVResponse(**result)
```

**Error Handling:**

```python
# Validation errors (400)
- Missing both job_description and job_link
- Invalid URL format
- Missing required fields

# Scraping errors (400)
- Timeout
- 404 Not Found
- 403 Forbidden
- Parsing failure

# Business logic errors (400)
- No active CV
- CV not parsed yet
- Invalid tone/length values

# Server errors (500)
- AI service failure
- Storage upload failure
- Database errors
```

#### POST /api/v1/applications/generate-cover-letter-custom

**Similar structure to CV endpoint but:**
- Returns text instead of file
- Uses CoverLetterGenerator
- Accepts `length` parameter instead of skill highlighting options

### Database Schema

#### Temporary Job Records

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    title VARCHAR(255),
    company VARCHAR(255),
    description TEXT,
    location VARCHAR(255),
    job_type VARCHAR(50),
    remote_type VARCHAR(50),
    job_link TEXT,
    source VARCHAR(50),  -- 'custom' for user-generated
    posted_date TIMESTAMP,
    expires_at TIMESTAMP NULL,
    match_score FLOAT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Custom Jobs:**
- Source: `'custom'`
- Job Link: Original URL or placeholder
- Never used for system recommendations
- Created per-application
- Can be cleaned up periodically

#### Application Records

```sql
CREATE TABLE applications (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    job_id UUID REFERENCES jobs(id),
    cv_id UUID REFERENCES cvs(id),
    tailored_cv_path VARCHAR(500),  -- Supabase path
    cover_letter TEXT,              -- Full text
    status VARCHAR(50),             -- 'draft', 'submitted', etc.
    generation_settings JSONB,      -- Tone, skills, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Generation Settings:**
```json
{
    "tone": "professional",
    "highlight_skills": true,
    "emphasize_relevant_experience": true,
    "custom_job": true,
    "type": "cv"  // or "cover_letter" or "both"
}
```

### Security Considerations

#### Input Sanitization

**URL Validation:**
```python
from urllib.parse import urlparse

parsed = urlparse(url)
if not parsed.scheme or not parsed.netloc:
    raise ValueError("Invalid URL format")

# Whitelist schemes
if parsed.scheme not in ['http', 'https']:
    raise ValueError("Only HTTP/HTTPS URLs allowed")
```

**Content Sanitization:**
```python
# Already implemented in sanitizer.py
sanitized_cv = self.sanitizer.sanitize_cv_data(cv_data)
sanitized_job = self.sanitizer.sanitize_job_data(job_dict)
sanitized_profile = self.sanitizer.sanitize_profile_data(profile_dict)

# Checks for sensitive data
sensitive_found = self.sanitizer.check_for_sensitive_data(cv_text)
if sensitive_found:
    logger.warning(f"Sensitive data types found: {sensitive_found}")
```

#### Rate Limiting

**Recommended Limits:**
```python
@router.post("/generate-cv-custom")
@limiter.limit("10/hour")  # 10 requests per hour per user
@limiter.limit("100/day")  # 100 requests per day per user
async def generate_tailored_cv_custom(...):
    ...
```

#### Authentication

**Required for all endpoints:**
```python
current_user: dict = Depends(get_current_user)
# Returns: {"id": "uuid", "email": "user@example.com", ...}
```

**JWT Token:**
- Bearer token in Authorization header
- Verified by `get_current_user` dependency
- Expires after configured time

### Performance Optimization

#### Caching Strategy

**Not currently implemented, but recommended:**

```python
# Cache scraped job descriptions
@cached(ttl=3600)  # 1 hour
def scrape_job_from_url(url: str) -> Dict[str, Any]:
    ...

# Benefits:
- Reduces scraping load
- Faster response for same URLs
- Less strain on job boards
- Better UX

# Cache invalidation:
- TTL-based (1 hour)
- Or manual clear on errors
```

#### Async Processing

**Current Implementation:**
```python
# Synchronous in request handler
result = await cv_generator.generate_tailored_cv_from_custom_description(...)
```

**Recommended for Scale:**
```python
# Background task with Celery
task_id = generate_cv_task.delay(user_id, job_data)

# Return task ID immediately
return {"task_id": task_id, "status": "processing"}

# Client polls for completion
GET /api/v1/applications/task/{task_id}
```

#### Database Indexing

**Recommended Indexes:**
```sql
CREATE INDEX idx_applications_user_id ON applications(user_id);
CREATE INDEX idx_applications_job_id ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_cvs_user_active ON cvs(user_id, is_active);
```

### Testing

#### Unit Tests

**Job Scraper Tests:**
```python
def test_scrape_linkedin_valid_url():
    scraper = JobDescriptionScraper()
    result = scraper.scrape_job_from_url("https://linkedin.com/jobs/view/123")
    assert result['title']
    assert result['company']
    assert result['description']
    assert result['source'] == 'LinkedIn'

def test_scrape_invalid_url():
    scraper = JobDescriptionScraper()
    with pytest.raises(ValueError, match="Invalid URL"):
        scraper.scrape_job_from_url("not-a-url")

def test_scrape_expired_job():
    scraper = JobDescriptionScraper()
    with pytest.raises(ValueError, match="not found"):
        scraper.scrape_job_from_url("https://linkedin.com/jobs/view/expired")
```

**CV Generator Tests:**
```python
@pytest.mark.asyncio
async def test_generate_cv_with_link(test_db, mock_cv, mock_ai):
    generator = CVGenerator()
    result = await generator.generate_tailored_cv_from_custom_description(
        user_id="test-user",
        job_title="Engineer",
        company_name="Tech Corp",
        job_description="Job description...",
        db=test_db
    )
    assert result['status'] == 'completed'
    assert result['cv_path']
    assert result['application_id']
```

#### Integration Tests

**API Endpoint Tests:**
```python
def test_generate_cv_endpoint(client, auth_token):
    response = client.post(
        "/api/v1/applications/generate-cv-custom",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "job_link": "https://linkedin.com/jobs/view/123",
            "tone": "professional"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data['application_id']
    assert data['public_url']
```

### Monitoring & Logging

#### Key Metrics

**Application Metrics:**
```python
# Success/failure rates
cv_generation_success_rate = successful / total
cover_letter_generation_success_rate = successful / total

# Response times
avg_scraping_time = sum(times) / count
avg_cv_generation_time = sum(times) / count

# Error rates by type
scraping_errors_by_type = {
    '404': count,
    '403': count,
    'timeout': count,
    ...
}

# Usage patterns
generations_by_job_board = {
    'linkedin': count,
    'indeed': count,
    ...
}
```

**Logging Strategy:**

```python
# Info level - normal operations
logger.info(f"Scraping job from URL: {url}")
logger.info(f"Successfully scraped: {title} at {company}")
logger.info(f"CV generated for user {user_id}")

# Warning level - recoverable issues
logger.warning(f"Scraping failed, using manual input")
logger.warning(f"Sensitive data found in CV")

# Error level - failures
logger.error(f"Failed to scrape: {error}", exc_info=True)
logger.error(f"CV generation failed: {error}", exc_info=True)
```

### Deployment

#### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_KEY=...
SUPABASE_STORAGE_BUCKET=cvs
JWT_SECRET=...
OPENAI_API_KEY=...  # or other AI provider

# Optional
SCRAPER_TIMEOUT=15  # seconds
SCRAPER_USER_AGENT="Mozilla/5.0 ..."
MAX_GENERATIONS_PER_HOUR=10
MAX_GENERATIONS_PER_DAY=100
```

#### Dependencies

```bash
# Backend
pip install -r requirements.txt

# New dependencies for this feature:
beautifulsoup4>=4.12.0
requests>=2.32.3  # (already present)
```

#### Database Migrations

```sql
-- If custom job cleanup needed:
DELETE FROM jobs 
WHERE source = 'custom' 
AND created_at < NOW() - INTERVAL '90 days'
AND id NOT IN (
    SELECT DISTINCT job_id FROM applications
);
```

## Frontend Implementation

### Component Structure

```
app/dashboard/cv/custom/
└── page.tsx                 # Main component (600+ lines)
    ├── State Management     # useState hooks
    ├── Data Fetching        # useEffect, API calls
    ├── Input Handlers       # Form validation
    ├── Generation Handlers  # CV & Cover Letter
    └── UI Components        # Tabs, forms, results
```

### Key State Variables

```typescript
// CV Data
const [activeCV, setActiveCV] = useState<CVDetail | null>(null)

// Loading States
const [loading, setLoading] = useState(true)
const [generatingCV, setGeneratingCV] = useState(false)
const [generatingCoverLetter, setGeneratingCoverLetter] = useState(false)

// Results
const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
const [coverLetterText, setCoverLetterText] = useState<string | null>(null)

// Form
const [inputMode, setInputMode] = useState<'description' | 'link'>('link')
const [jobLink, setJobLink] = useState('')
const [jobDescription, setJobDescription] = useState('')
const [jobTitle, setJobTitle] = useState('')
const [companyName, setCompanyName] = useState('')

// Options
const [tone, setTone] = useState<'professional' | ...>('professional')
const [coverLetterLength, setCoverLetterLength] = useState<'short' | ...>('medium')
const [showAdvanced, setShowAdvanced] = useState(false)
```

### API Client

**Location:** `lib/api/applications.ts`

```typescript
export async function generateCustomTailoredCV(
  request: GenerateCustomCVRequest
): Promise<GenerateCVResponse> {
  return apiClient.post<GenerateCVResponse>(
    `/api/v1/applications/generate-cv-custom`,
    request
  )
}

export async function generateCustomCoverLetter(
  request: GenerateCoverLetterRequest
): Promise<GenerateCoverLetterResponse> {
  return apiClient.post<GenerateCoverLetterResponse>(
    `/api/v1/applications/generate-cover-letter-custom`,
    request
  )
}
```

### Validation Logic

```typescript
const validateInput = () => {
  if (inputMode === 'link') {
    if (!jobLink.trim()) {
      toast.error('Please enter a job posting URL')
      return false
    }
    // URL validation
    try {
      new URL(jobLink.trim())
    } catch {
      toast.error('Please enter a valid URL')
      return false
    }
  } else {
    // Manual description validation
    if (!jobDescription.trim()) {
      toast.error('Please enter a job description')
      return false
    }
    if (!jobTitle.trim() || !companyName.trim()) {
      toast.error('Job title and company required')
      return false
    }
  }
  return true
}
```

### Error Handling

```typescript
try {
  const result = await generateCustomTailoredCV({...})
  toast.success('CV generated successfully!')
  setDownloadUrl(result.public_url)
} catch (error: any) {
  const errorMessage = 
    error.response?.data?.detail ||  // Backend error
    error.message ||                  // Network error
    'Failed to generate CV'           // Fallback
  toast.error(errorMessage)
}
```

## Development Workflow

### Local Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Testing New Features

```bash
# Backend tests
cd backend
pytest tests/ -v

# Specific test file
pytest tests/test_job_scraper.py -v

# Frontend build check
cd frontend
npm run build
npm run lint
```

### Code Quality

```bash
# Backend
black app/  # Format
flake8 app/  # Lint
mypy app/  # Type check

# Frontend
npm run lint  # ESLint
npm run type-check  # TypeScript
```

## Future Enhancements

### Planned Features

1. **Caching Layer**
   - Redis for scraped job data
   - Cache CV generations
   - Reduce API calls

2. **Async Processing**
   - Celery tasks for generation
   - WebSocket progress updates
   - Better scalability

3. **Enhanced Scraping**
   - JavaScript rendering (Playwright)
   - More job boards
   - Better rate limit handling

4. **Analytics**
   - Track generation success rates
   - Popular job boards
   - User patterns

5. **Batch Processing**
   - Generate for multiple jobs
   - Bulk operations
   - Queue management

### Technical Debt

- [ ] Add comprehensive unit tests
- [ ] Implement request rate limiting
- [ ] Add caching layer
- [ ] Move to async processing
- [ ] Add health check endpoints
- [ ] Implement circuit breakers
- [ ] Add metrics collection
- [ ] Improve error recovery

## Support

**For Developers:**
- Review code comments
- Check inline documentation
- Run test suite
- Enable debug logging

**For Issues:**
- Check logs first
- Include full error message
- Provide reproduction steps
- Note environment details

---

*Last Updated: January 2024*
*For: Developers and Technical Staff*
