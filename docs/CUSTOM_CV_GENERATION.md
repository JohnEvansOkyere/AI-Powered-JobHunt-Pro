# Custom CV & Cover Letter Generation Feature

## Overview

The Custom CV & Cover Letter Generation feature allows users to paste any job description from any source (LinkedIn, Indeed, company websites, etc.) and generate both a tailored CV and a personalized cover letter instantly, without needing the job to be in the system's database.

## Feature Details

### What It Does

- Users can paste job descriptions manually into a form
- **Generate Tailored CV**: The AI analyzes the job requirements and tailors the user's CV to highlight relevant experience and skills
- **Generate Cover Letter**: The AI writes a personalized, professional cover letter for the specific position
- The generated CV maintains the user's original formatting (for DOCX files) or creates a professional new format
- The cover letter is formatted and ready to copy or customize further
- The original CV remains unchanged - new customized versions are created

### How It Works

1. **User Uploads Base CV**: User must have an active CV uploaded to the system (done in CV Management page)

2. **User Provides Job Details**:
   - Job Title (required)
   - Company Name (required)
   - Job Description (required) - can be full job posting text
   - Location (optional)
   - Job Type (optional: full-time, part-time, contract, internship)
   - Remote Type (optional: remote, hybrid, on-site)

3. **Customization Options**:
   - **Tone**: Professional, Confident, Friendly, or Enthusiastic
   - **Highlight Skills** (CV only): Emphasize skills matching job requirements
   - **Emphasize Experience** (CV only): Highlight relevant work experience
   - **Cover Letter Length**: Short (3 paragraphs), Medium (4 paragraphs), Long (5 paragraphs)

4. **AI Processing**:
   - Creates a temporary job record for tracking
   - Uses AI to generate tailored content
   - **For CV**: Downloads original CV, applies tailoring while preserving format
   - **For Cover Letter**: Generates personalized letter with proper business format
   - Sanitizes all inputs for security
   - Highlights relevant experience and skills

5. **Output**:
   - **CV**: Downloadable file (DOCX or new format)
   - **Cover Letter**: Text displayed in-app with copy-to-clipboard functionality
   - Both are saved to database and linked to application records

## Technical Implementation

### Backend

#### Endpoints

**1. Generate CV: `/api/v1/applications/generate-cv-custom`**

**Method**: POST

**Request Body**:
```json
{
  "job_title": "Senior Software Engineer",
  "company_name": "Tech Corp",
  "job_description": "Full job description text...",
  "location": "San Francisco, CA",
  "job_type": "full-time",
  "remote_type": "hybrid",
  "tone": "professional",
  "highlight_skills": true,
  "emphasize_relevant_experience": true
}
```

**Response**:
```json
{
  "application_id": "uuid",
  "cv_path": "storage/path/to/cv.docx",
  "public_url": "https://...",
  "status": "completed",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**2. Generate Cover Letter: `/api/v1/applications/generate-cover-letter-custom`**

**Method**: POST

**Request Body**:
```json
{
  "job_title": "Senior Software Engineer",
  "company_name": "Tech Corp",
  "job_description": "Full job description text...",
  "location": "San Francisco, CA",
  "job_type": "full-time",
  "remote_type": "hybrid",
  "tone": "professional",
  "length": "medium"
}
```

**Response**:
```json
{
  "application_id": "uuid",
  "cover_letter": "Full cover letter text...",
  "status": "completed",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Services

**cv_generator.py** - `generate_tailored_cv_from_custom_description()`
- Creates temporary job record
- Downloads original CV file
- Uses AI to generate tailored content
- Preserves formatting (DOCX) or creates new format
- Saves to storage

**cover_letter_generator.py** - `generate_cover_letter_from_custom_description()`
- Creates temporary job record
- Extracts applicant info from CV
- Uses AI to write personalized cover letter
- Formats with proper business letter structure
- Saves to database

### Frontend

#### New Page: `/dashboard/cv/custom`

Features:
- Clean form for entering job details
- Text area for pasting full job descriptions
- Optional fields for additional context
- Customization options (tone, highlighting preferences, cover letter length)
- **Two action buttons**: "Generate Tailored CV" and "Generate Cover Letter"
- Real-time validation
- Success states:
  - CV: Green box with download button
  - Cover Letter: Blue box with formatted text and copy-to-clipboard button
- Info sections explaining both features

#### Navigation

- Button added to CV Management page: "Generate Custom CV"
- Accessible from `/dashboard/cv` → "Generate Custom CV" button
- Page title: "Generate Custom CV & Cover Letter"

## User Flow

1. User navigates to CV Management (`/dashboard/cv`)
2. User clicks "Generate Custom CV" button
3. User fills in job details form:
   - Pastes job description from any source
   - Fills in job title, company name
   - Optionally adds location, job type, remote preference
   - Selects tone and customization options
   - Chooses cover letter length
4. User has two options:
   - Click "Generate Tailored CV" → Downloads customized CV file
   - Click "Generate Cover Letter" → Displays formatted cover letter with copy button
5. User can generate both for the same job description
6. User can copy cover letter to clipboard or download CV
7. User can generate for another job or navigate away

## Security

- All inputs are sanitized using the existing sanitizer utility
- Job descriptions are checked for sensitive data
- CV data is limited to prevent excessive AI token usage
- Authentication required for all endpoints
- File storage uses secure Supabase Storage

## Database Impact

- Creates a temporary `Job` record with `source: "custom"`
- Creates an `Application` record linking the CV to the custom job
- Custom jobs are marked with `generation_settings.custom_job: true`

## Files Modified/Created

### Backend Files
- `backend/app/api/v1/endpoints/applications.py` - Added CV and cover letter endpoints and request models
- `backend/app/services/cv_generator.py` - Added method for custom job descriptions
- `backend/app/services/cover_letter_generator.py` - **NEW** - Complete cover letter generation service

### Frontend Files
- `frontend/app/dashboard/cv/custom/page.tsx` - Updated page with two generation buttons and cover letter display
- `frontend/app/dashboard/cv/page.tsx` - Added button to access custom generation
- `frontend/lib/api/applications.ts` - Added API client functions for both CV and cover letter generation

### Documentation
- `docs/CUSTOM_CV_GENERATION.md` - This file (updated to include cover letter feature)

## Limitations

1. User must have an active CV uploaded
2. CV must be successfully parsed (status: "completed")
3. Job description quality affects CV tailoring quality
4. Very long job descriptions may be truncated for AI processing
5. Custom jobs are stored in database (may want periodic cleanup)

## Future Enhancements

- Ability to save custom job descriptions for later use
- Preview of tailored content before generating
- Bulk generation from multiple job descriptions
- Templates for common job posting sources
- Integration with browser extension to auto-fill from job sites
- Comparison view showing original vs. tailored CV
- Analytics on which custom jobs get best results
- Email integration to send cover letters directly
- Multiple cover letter variations for A/B testing
- Cover letter templates for different industries

## Testing

To test the feature:

1. Ensure backend is running
2. Log in to the application
3. Upload a CV in CV Management (DOCX recommended)
4. Wait for CV parsing to complete
5. Click "Generate Custom CV" button
6. Fill in all required fields with a real job description
7. Click "Generate Tailored CV"
8. Wait for processing (check browser console for errors)
9. Download and review the generated CV

## Troubleshooting

### "No active CV found"
- User needs to upload a CV first
- Check CV Management page

### "CV has not been parsed yet"
- Wait for CV parsing to complete
- Check CV status in CV Management

### Generation fails with 500 error
- Check backend logs for AI service errors
- Verify AI provider credentials are configured
- Check storage permissions

### Generated CV doesn't preserve formatting
- For best results, upload DOCX files (not PDF)
- PDF files will generate a new formatted document

### Job description too long
- Sanitizer may truncate very long descriptions
- Try condensing to key requirements and responsibilities

## Notes

- The feature uses the same AI tailoring logic as the regular job-based CV generation
- Custom jobs are stored with `source: "custom"` for easy filtering
- The application record links to both the CV and the custom job
- Generated CVs are stored in `tailored-cvs/{user_id}/custom_{timestamp}_{filename}`
