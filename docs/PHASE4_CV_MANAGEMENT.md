# Phase 4: CV Management - Documentation

## Overview

Phase 4 implements complete CV (Resume) management functionality, allowing users to upload, parse, view, and manage their CV files. The system supports PDF and DOCX formats, extracts structured data using AI, and stores files securely in Supabase Storage.

**Status**: ✅ Complete  
**Date Completed**: December 2024

---

## Features Implemented

### 1. CV Upload
- ✅ File upload via drag-and-drop or file picker
- ✅ Support for PDF and DOCX formats
- ✅ File size validation (max 10MB)
- ✅ Upload to Supabase Storage
- ✅ Automatic parsing trigger

### 2. CV Parsing
- ✅ Text extraction from PDF (PyPDF2 + pdfplumber fallback)
- ✅ Text extraction from DOCX (python-docx)
- ✅ AI-powered structured data extraction
- ✅ Parsing status tracking (pending, processing, completed, failed)
- ✅ Error handling and reporting

### 3. CV Management
- ✅ List all CVs for a user
- ✅ Get active CV
- ✅ Get specific CV with parsed content
- ✅ Activate/deactivate CVs
- ✅ Delete CVs (removes from storage and database)
- ✅ Generate signed download URLs

### 4. Frontend UI
- ✅ CV upload page with drag-and-drop
- ✅ Active CV preview with extracted information
- ✅ CV list with status indicators
- ✅ Download and delete functionality
- ✅ Real-time parsing status updates

---

## Architecture

### Backend Components

#### 1. CV Parser Service (`backend/app/services/cv_parser.py`)

**Responsibilities**:
- Extract raw text from PDF/DOCX files
- Use AI to extract structured data from CV text
- Handle parsing errors gracefully

**Key Methods**:
- `parse_pdf(file_content: bytes) -> str`: Extract text from PDF
- `parse_docx(file_content: bytes) -> str`: Extract text from DOCX
- `extract_text(file_content: bytes, file_type: str) -> str`: Unified text extraction
- `extract_structured_data(raw_text: str) -> Dict`: AI-powered data extraction
- `parse_cv(file_content: bytes, file_type: str) -> Dict`: Complete parsing pipeline

**Structured Data Format**:
```json
{
  "personal_info": {
    "name": "Full name",
    "email": "Email address",
    "phone": "Phone number",
    "location": "City, Country",
    "linkedin": "LinkedIn URL",
    "github": "GitHub URL",
    "website": "Personal website"
  },
  "summary": "Professional summary",
  "experience": [
    {
      "title": "Job title",
      "company": "Company name",
      "location": "Location",
      "start_date": "Start date",
      "end_date": "End date or 'Present'",
      "description": "Job description",
      "achievements": ["Achievement 1", "Achievement 2"]
    }
  ],
  "education": [
    {
      "degree": "Degree name",
      "institution": "Institution name",
      "location": "Location",
      "graduation_date": "Graduation date",
      "gpa": "GPA if mentioned"
    }
  ],
  "skills": {
    "technical": ["Skill 1", "Skill 2"],
    "languages": ["Language 1", "Language 2"],
    "certifications": ["Certification 1"]
  },
  "projects": [
    {
      "name": "Project name",
      "description": "Project description",
      "technologies": ["Tech 1", "Tech 2"],
      "url": "Project URL"
    }
  ]
}
```

#### 2. CV API Endpoints (`backend/app/api/v1/endpoints/cvs.py`)

**Endpoints**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/cvs/upload` | Upload a CV file |
| `GET` | `/api/v1/cvs/` | List all CVs for user |
| `GET` | `/api/v1/cvs/active` | Get active CV with parsed content |
| `GET` | `/api/v1/cvs/{cv_id}` | Get specific CV with parsed content |
| `POST` | `/api/v1/cvs/{cv_id}/activate` | Activate a CV (deactivates others) |
| `DELETE` | `/api/v1/cvs/{cv_id}` | Delete a CV |
| `GET` | `/api/v1/cvs/{cv_id}/download-url` | Get signed download URL |

**Request/Response Models**:
- `CVResponse`: Basic CV information
- `CVDetailResponse`: CV with parsed content and raw text

#### 3. Database Model (`backend/app/models/cv.py`)

**CV Model Fields**:
- `id`: UUID primary key
- `user_id`: Foreign key to auth.users
- `file_name`: Original filename
- `file_path`: Supabase Storage path
- `file_size`: File size in bytes
- `file_type`: 'pdf' or 'docx'
- `mime_type`: MIME type
- `parsed_content`: JSONB structured data
- `raw_text`: Full extracted text
- `parsing_status`: 'pending', 'processing', 'completed', 'failed'
- `parsing_error`: Error message if parsing failed
- `is_active`: Boolean flag (only one active per user)
- `created_at`, `updated_at`: Timestamps

### Frontend Components

#### 1. CV API Client (`frontend/lib/api/cvs.ts`)

**Functions**:
- `uploadCV(file: File)`: Upload CV file
- `getCVs()`: Get all CVs
- `getActiveCV()`: Get active CV
- `getCV(cvId: string)`: Get specific CV
- `activateCV(cvId: string)`: Activate a CV
- `deleteCV(cvId: string)`: Delete a CV
- `getCVDownloadURL(cvId: string)`: Get download URL

#### 2. CV Management Page (`frontend/app/dashboard/cv/page.tsx`)

**Features**:
- Drag-and-drop upload area
- File picker fallback
- Active CV preview with extracted information
- CV list with status indicators
- Download and delete actions
- Real-time status updates

---

## Setup Instructions

### 1. Supabase Storage Configuration

1. Go to Supabase Dashboard → Storage
2. Create a bucket named `cvs` (or update `SUPABASE_STORAGE_BUCKET` in backend config)
3. Set bucket to **Private** (RLS enabled)
4. Add storage policy:

```sql
-- Allow users to upload their own files
CREATE POLICY "Users can upload their own CVs"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'cvs' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Allow users to read their own files
CREATE POLICY "Users can read their own CVs"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'cvs' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Allow users to delete their own files
CREATE POLICY "Users can delete their own CVs"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'cvs' AND auth.uid()::text = (storage.foldername(name))[1]);
```

### 2. Backend Dependencies

Ensure these packages are installed:
```bash
pip install PyPDF2 pdfplumber python-docx
```

### 3. Environment Variables

No additional environment variables needed beyond existing Supabase configuration.

---

## Usage Examples

### Upload CV (Frontend)

```typescript
import { uploadCV } from '@/lib/api/cvs'

const file = event.target.files[0]
const cv = await uploadCV(file)
console.log('CV uploaded:', cv.id)
```

### Get Active CV (Frontend)

```typescript
import { getActiveCV } from '@/lib/api/cvs'

const activeCV = await getActiveCV()
if (activeCV) {
  console.log('Active CV:', activeCV.file_name)
  console.log('Parsed content:', activeCV.parsed_content)
}
```

### Upload CV (Backend API)

```bash
curl -X POST "http://localhost:8000/api/v1/cvs/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@resume.pdf"
```

### Get CVs (Backend API)

```bash
curl -X GET "http://localhost:8000/api/v1/cvs/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## File Storage Structure

Files are stored in Supabase Storage with the following structure:
```
cvs/
  {user_id}/
    {cv_id}.pdf
    {cv_id}.docx
```

Example:
```
cvs/
  d1be0de9-4491-485c-b898-85fef80a348f/
    a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf
```

---

## Parsing Process

1. **File Upload**: User uploads PDF or DOCX file
2. **Storage**: File saved to Supabase Storage
3. **Database Record**: CV record created with `parsing_status = 'pending'`
4. **Text Extraction**: 
   - PDF: PyPDF2 (with pdfplumber fallback)
   - DOCX: python-docx
5. **AI Extraction**: Raw text sent to AI model for structured extraction
6. **Status Update**: 
   - Success: `parsing_status = 'completed'`, data saved
   - Failure: `parsing_status = 'failed'`, error saved

---

## Error Handling

### Upload Errors
- **Invalid file type**: Returns 400 with error message
- **File too large**: Returns 400 (max 10MB)
- **Storage error**: Returns 500 with error details

### Parsing Errors
- **Empty file**: Sets status to 'failed' with error message
- **Unreadable file**: Sets status to 'failed' with error message
- **AI extraction failure**: Falls back to basic structure, logs error

### Frontend Error Handling
- Toast notifications for all errors
- Status indicators for parsing state
- Retry mechanisms for failed uploads

---

## Security Considerations

1. **File Type Validation**: Only PDF and DOCX allowed
2. **File Size Limits**: Maximum 10MB per file
3. **User Isolation**: Users can only access their own CVs
4. **RLS Policies**: Supabase Storage policies enforce access control
5. **Signed URLs**: Download URLs expire after 1 hour

---

## Performance Optimizations

1. **Async Parsing**: Parsing happens asynchronously (can be moved to Celery)
2. **Fallback Parsers**: Multiple PDF parsers for reliability
3. **Text Limiting**: AI prompts limited to 4000 characters to avoid token limits
4. **Lazy Loading**: Parsed content only loaded when needed

---

## Future Enhancements

1. **Background Processing**: Move parsing to Celery tasks
2. **Multiple CV Versions**: Support for multiple active CVs
3. **CV Comparison**: Compare different CV versions
4. **CV Templates**: Generate CVs from templates
5. **Export Formats**: Export to different formats (PDF, DOCX, HTML)
6. **CV Analytics**: Track CV views and downloads
7. **Version History**: Track changes to CVs over time

---

## Testing

### Manual Testing Checklist

- [ ] Upload PDF CV
- [ ] Upload DOCX CV
- [ ] Verify file appears in list
- [ ] Check parsing status updates
- [ ] View parsed content
- [ ] Download CV
- [ ] Delete CV
- [ ] Activate different CV
- [ ] Test file size limit (10MB)
- [ ] Test invalid file type
- [ ] Test drag-and-drop upload
- [ ] Test file picker upload

### API Testing

```bash
# Upload CV
curl -X POST "http://localhost:8000/api/v1/cvs/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_resume.pdf"

# List CVs
curl -X GET "http://localhost:8000/api/v1/cvs/" \
  -H "Authorization: Bearer $TOKEN"

# Get Active CV
curl -X GET "http://localhost:8000/api/v1/cvs/active" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting

### Issue: CV parsing fails
**Solution**: Check AI API keys are configured, verify file is readable

### Issue: File upload fails
**Solution**: Check Supabase Storage bucket exists and policies are set

### Issue: Download URL doesn't work
**Solution**: Verify signed URL generation, check expiration time

### Issue: Parsed content is empty
**Solution**: Check AI model response, verify text extraction worked

---

## Related Documentation

- [Phase 3: User Profile System](./PHASE3_PROFILE.md)
- [Phase 5: AI Model Router](./PHASE5_AI_ROUTER.md) (when completed)
- [Supabase Storage Setup](./SETUP.md#configure-storage)
- [Database Schema](./SUPABASE_SCHEMA.sql)

---

## Summary

Phase 4 successfully implements a complete CV management system with:
- ✅ Secure file upload and storage
- ✅ Intelligent text extraction
- ✅ AI-powered structured data extraction
- ✅ Full CRUD operations
- ✅ User-friendly frontend interface
- ✅ Comprehensive error handling

The system is production-ready and provides a solid foundation for Phase 8 (AI Application Generation), where CVs will be tailored for specific job applications.

