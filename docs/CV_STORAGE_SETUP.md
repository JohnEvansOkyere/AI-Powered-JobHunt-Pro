# CV Storage Setup Guide

## Problem

When generating a tailored CV, you get error: **"Bucket not found" (404)**

This means the Supabase storage bucket for CVs hasn't been created yet.

## Solution: Create Supabase Storage Bucket

### Step 1: Create the 'cvs' Bucket

1. **Go to Supabase Dashboard**: https://supabase.com/dashboard
2. **Select your project**
3. **Navigate to Storage** (left sidebar, folder icon)
4. **Click "Create a new bucket"** (green button)
5. **Configure the bucket**:
   - **Bucket ID**: `cvs`
   - **Bucket name**: `cvs`
   - **Public bucket**: ❌ **UNCHECK** (keep private)
   - **Allowed MIME types**: Add these:
     - `application/pdf`
     - `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (DOCX)
     - `text/markdown`
   - **Max file size**: 10 MB (10485760 bytes)
6. **Click "Create bucket"**

### Step 2: Apply Storage Policies

The storage policies are already in [docs/SUPABASE_SETUP_COMPLETE.sql](SUPABASE_SETUP_COMPLETE.sql) (lines 623-658).

**Run this in Supabase SQL Editor** (after creating the bucket):

```sql
-- Policy: Users can upload their own CVs
CREATE POLICY "Users can upload their own CVs"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'cvs'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Policy: Users can read their own CVs
CREATE POLICY "Users can read their own CVs"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'cvs'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Policy: Users can update their own CVs
CREATE POLICY "Users can update their own CVs"
ON storage.objects FOR UPDATE
TO authenticated
USING (
  bucket_id = 'cvs'
  AND auth.uid()::text = (storage.foldername(name))[1]
)
WITH CHECK (
  bucket_id = 'cvs'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Policy: Users can delete their own CVs
CREATE POLICY "Users can delete their own CVs"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'cvs'
  AND auth.uid()::text = (storage.foldername(name))[1]
);
```

### Step 3: Verify Setup

Run this test in Supabase SQL Editor:

```sql
-- Check bucket exists
SELECT * FROM storage.buckets WHERE id = 'cvs';

-- Check policies exist
SELECT * FROM pg_policies WHERE tablename = 'objects' AND policyname LIKE '%CV%';
```

You should see:
- 1 bucket named 'cvs'
- 4 policies for CV management

## How CV Storage Works

### Original CV Upload
When a user uploads their CV:
- **Path**: `{user_id}/{cv_id}.{extension}`
- **Example**: `550e8400-e29b-41d4-a716-446655440000/abc123.pdf`
- **Stored in**: `cvs` bucket
- **Record**: Saved in `cvs` table in database

### Tailored CV Generation
When a user generates a tailored CV for a job:
1. **Backend reads** the original CV from `cvs` bucket
2. **AI generates** tailored content based on job requirements
3. **Backend saves** the new tailored CV to `cvs` bucket:
   - **Path**: `tailored-cvs/{user_id}/tailored_cv_{job_id}_{timestamp}.md`
   - **Example**: `tailored-cvs/550e8400/tailored_cv_job123_20250109_120000.md`
4. **Database record** created in `applications` table with path

**Key Points**:
- ✅ Original CV is **never modified**
- ✅ Tailored CVs are stored separately in `tailored-cvs/` folder
- ✅ Each tailored CV is timestamped
- ✅ You can generate multiple tailored CVs from the same original CV

## File Structure in Storage

```
cvs/ (bucket)
├── {user_id_1}/
│   ├── cv_abc123.pdf         ← Original uploaded CV
│   └── cv_def456.docx        ← Another original CV
├── {user_id_2}/
│   └── cv_xyz789.pdf
└── tailored-cvs/
    ├── {user_id_1}/
    │   ├── tailored_cv_job1_20250109_120000.md  ← Tailored for Job 1
    │   ├── tailored_cv_job2_20250109_130000.md  ← Tailored for Job 2
    │   └── tailored_cv_job1_20250110_140000.md  ← Regenerated for Job 1
    └── {user_id_2}/
        └── tailored_cv_job3_20250109_150000.md
```

## Database Schema

### `cvs` Table
Stores original CV metadata:
```sql
- id (UUID)
- user_id (UUID)
- file_name (text)
- file_path (text)  ← Path in storage: "{user_id}/{cv_id}.ext"
- is_active (boolean)
```

### `applications` Table
Stores tailored CV info:
```sql
- id (UUID)
- user_id (UUID)
- job_id (UUID)
- cv_id (UUID) ← References original CV
- tailored_cv_path (text) ← Path in storage: "tailored-cvs/{user_id}/..."
- status (text)
```

## Troubleshooting

### Error: "Bucket not found"
- **Cause**: The 'cvs' bucket doesn't exist
- **Fix**: Create the bucket (Step 1 above)

### Error: "Permission denied"
- **Cause**: Storage policies not applied
- **Fix**: Run the SQL policies (Step 2 above)

### Error: "File too large"
- **Cause**: File exceeds 10 MB limit
- **Fix**: Increase max file size in bucket settings

### Tailored CV not generating
1. Check backend logs: `tail -f backend/logs/app.log`
2. Verify original CV exists: Check `cvs` table in database
3. Verify CV is parsed: Check `parsing_status = 'completed'` in `cvs` table
4. Check OpenAI API key is set: `OPENAI_API_KEY` in `.env`

## Testing

### Test Original CV Upload

```bash
curl -X POST http://localhost:8000/api/v1/cvs/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/cv.pdf"
```

Expected response:
```json
{
  "id": "cv-id",
  "file_name": "cv.pdf",
  "file_path": "{user_id}/{cv_id}.pdf",
  "parsing_status": "pending"
}
```

### Test Tailored CV Generation

```bash
curl -X POST http://localhost:8000/api/v1/applications/generate-cv \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-id",
    "tone": "professional"
  }'
```

Expected response:
```json
{
  "application_id": "app-id",
  "cv_path": "tailored-cvs/{user_id}/tailored_cv_{job_id}_{timestamp}.md",
  "public_url": "https://...",
  "status": "completed"
}
```

## Next Steps

1. ✅ Create the 'cvs' bucket in Supabase
2. ✅ Apply storage policies
3. ✅ Test by uploading a CV
4. ✅ Test by generating a tailored CV
5. 🎯 Enjoy automated CV tailoring!

---

**Updated**: 2025-01-09
**Status**: Required for CV features to work
