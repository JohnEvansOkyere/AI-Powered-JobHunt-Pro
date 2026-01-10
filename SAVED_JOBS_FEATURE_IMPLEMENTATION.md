# Saved Jobs Feature Implementation Progress

## ✅ Completed

### 1. Database Changes
**File**: [backend/app/models/application.py](backend/app/models/application.py)
- ✅ Added `saved_at` column (timestamp when saved)
- ✅ Added `expires_at` column (saved_at + 10 days)
- ✅ Expanded `status` field: `'saved'`, `'draft'`, `'reviewed'`, `'finalized'`, `'sent'`, `'submitted'`, `'interviewing'`, `'rejected'`, `'offer'`
- ✅ Default status changed to `'saved'`

**Migration**: [migrations/003_add_saved_jobs_feature.sql](migrations/003_add_saved_jobs_feature.sql)
- Run this SQL in Supabase SQL Editor to apply changes

### 2. Backend API Endpoints
**File**: [backend/app/api/v1/endpoints/applications.py](backend/app/api/v1/endpoints/applications.py)

**New Endpoints**:

```python
POST /api/v1/applications/save-job/{job_id}
- Saves a job (creates application with status='saved')
- Sets expires_at = now + 10 days
- Limit: 10 saved jobs max
- Returns: ApplicationResponse

DELETE /api/v1/applications/unsave-job/{job_id}
- Removes a saved job
- Only works if status='saved'
- Returns: 204 No Content

GET /api/v1/applications/saved-jobs
- Lists all saved jobs for user
- Filters: status='saved'
- Ordered by: saved_at desc
- Returns: list[ApplicationResponse]
```

**Updated Response Model**:
- `ApplicationResponse` now includes `saved_at` and `expires_at` fields

### 3. Scheduler Cleanup Job
**File**: [backend/app/scheduler/job_scheduler.py](backend/app/scheduler/job_scheduler.py)

**New Job**:
```python
cleanup_expired_saved_jobs()
- Runs daily at midnight UTC
- Deletes saved jobs where expires_at < now
- Logs deleted count
```

**Schedule**:
- Job Scraping: 6:00 AM UTC
- Saved Jobs Cleanup: Midnight UTC (12:00 AM)

### 4. Frontend API Client
**File**: [frontend/lib/api/savedJobs.ts](frontend/lib/api/savedJobs.ts)

```typescript
export async function saveJob(jobId: string): Promise<Application>
export async function unsaveJob(jobId: string): Promise<void>
export async function getSavedJobs(): Promise<Application[]>
```

### 5. Job Card Component
**File**: [frontend/components/jobs/JobCard.tsx](frontend/components/jobs/JobCard.tsx)

**Added "Save Job" Button**:
- ✅ Bookmark icon for unsaved jobs
- ✅ BookmarkCheck (filled) icon for saved jobs
- ✅ Props: `onSave?: (jobId: string) => void` and `isSaved?: boolean`
- ✅ Visual feedback (background color changes when saved)
- ✅ Tooltips: "Save for later" / "Remove from saved"

### 6. Jobs Page Integration
**File**: [frontend/app/dashboard/jobs/page.tsx](frontend/app/dashboard/jobs/page.tsx)

**Save/Unsave Handlers**:
```typescript
const [savedJobs, setSavedJobs] = useState<Set<string>>(new Set())

const handleSaveToggle = async (jobId: string) => {
  // Saves or unsaves job
  // Shows toast messages
  // Handles 10 job limit error
}
```

**Features**:
- ✅ Loads saved jobs on mount
- ✅ Save/unsave toggle with optimistic UI updates
- ✅ Toast notifications for success/error
- ✅ 10 job limit error handling
- ✅ Bookmark button state synced across page

### 7. Applications Page - Saved Jobs Tab
**File**: [frontend/app/dashboard/applications/page.tsx](frontend/app/dashboard/applications/page.tsx)

**Added Tabs**:
- ✅ **Saved Jobs** tab (default) - Shows bookmarked jobs
- ✅ **In Progress** tab - Shows draft/generated applications
- ✅ **Submitted** tab - Shows sent applications

**Saved Jobs Tab Features**:
```typescript
- Job count in tab label: "Saved Jobs (X)"
- Expiry countdown: "Expires in X days" (shows when ≤ 3 days left)
- Saved date display
- "Generate Tailored CV" button (navigates to generation page)
- "Remove" button (unsaves the job)
- Empty state with helpful message
- Loading state with spinner
```

## Feature Flow

### User Journey

1. **Browse Jobs**:
   - User visits Jobs page (Recommendations or All Jobs tab)
   - Each job card shows a bookmark icon

2. **Save a Job**:
   - User clicks bookmark icon
   - Job is saved with status='saved'
   - Expires in 10 days
   - Toast: "Job saved to Applications"
   - Icon changes to filled bookmark

3. **View Saved Jobs**:
   - User visits Applications page
   - Default tab shows "Saved Jobs"
   - See all saved jobs with expiry countdown
   - Jobs expiring soon (≤3 days) show orange badge

4. **Generate CV from Saved Job**:
   - User clicks "Generate Tailored CV" button
   - Navigates to CV generation page
   - Application status changes from 'saved' to 'draft'
   - Job moves from "Saved Jobs" tab to "In Progress" tab

5. **Remove Saved Job**:
   - User clicks "Remove" button
   - Job is deleted from applications
   - Bookmark icon updates across all pages

6. **Automatic Cleanup**:
   - Scheduler runs daily at midnight UTC
   - Deletes jobs where expires_at < now
   - Logs deleted count

## Technical Implementation Details

### Status Flow
```
'saved' (bookmarked, 10 day expiry)
   ↓
'draft' (CV generation started)
   ↓
'reviewed' (user reviewed materials)
   ↓
'finalized' (ready to send)
   ↓
'sent' / 'submitted'
   ↓
'interviewing' / 'rejected' / 'offer'
```

### Database Schema
```sql
ALTER TABLE applications
ADD COLUMN saved_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE applications
ADD CONSTRAINT applications_status_check
CHECK (status IN ('saved', 'draft', 'reviewed', 'finalized', 'sent', 'submitted', 'interviewing', 'rejected', 'offer'));
```

### API Contract

**Save Job**:
```http
POST /api/v1/applications/save-job/{job_id}
Authorization: Bearer <token>

Response 201:
{
  "id": "uuid",
  "user_id": "uuid",
  "job_id": "uuid",
  "status": "saved",
  "saved_at": "2026-01-10T12:00:00Z",
  "expires_at": "2026-01-20T12:00:00Z",
  "created_at": "2026-01-10T12:00:00Z",
  "updated_at": "2026-01-10T12:00:00Z"
}

Response 400 (limit reached):
{
  "detail": "You have reached the maximum limit of 10 saved jobs. Please remove some before saving more."
}
```

**Unsave Job**:
```http
DELETE /api/v1/applications/unsave-job/{job_id}
Authorization: Bearer <token>

Response 204: No Content

Response 404:
{
  "detail": "Saved job not found"
}
```

**Get Saved Jobs**:
```http
GET /api/v1/applications/saved-jobs
Authorization: Bearer <token>

Response 200:
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "job_id": "uuid",
    "status": "saved",
    "saved_at": "2026-01-10T12:00:00Z",
    "expires_at": "2026-01-20T12:00:00Z",
    "created_at": "2026-01-10T12:00:00Z",
    "updated_at": "2026-01-10T12:00:00Z"
  }
]
```

## Testing Checklist

### Backend
- [ ] Run migration SQL in Supabase
- [ ] Test save job endpoint: `POST /api/v1/applications/save-job/{job_id}`
- [ ] Test unsave job endpoint: `DELETE /api/v1/applications/unsave-job/{job_id}`
- [ ] Test get saved jobs: `GET /api/v1/applications/saved-jobs`
- [ ] Test 10 job limit (try saving 11th job)
- [ ] Verify scheduler logs show cleanup job scheduled

### Frontend
- [ ] Save button appears on job cards
- [ ] Click save → job appears in Applications > Saved Jobs tab
- [ ] Saved button shows checkmark/filled icon
- [ ] Click saved button again → job removed
- [ ] Expiry countdown shows correctly
- [ ] Generate CV from saved job → navigate to generation page
- [ ] Toast messages work correctly
- [ ] 10 job limit error shows

## Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Database Model | ✅ Done | Added columns, updated constraints |
| Migration SQL | ✅ Done | Ready to run in Supabase |
| Save Job API | ✅ Done | With 10 job limit |
| Unsave Job API | ✅ Done | Only for status='saved' |
| Get Saved Jobs API | ✅ Done | Returns list ordered by saved_at |
| Cleanup Scheduler | ✅ Done | Runs daily at midnight UTC |
| Frontend API Client | ✅ Done | savedJobs.ts with 3 functions |
| Save Button on Job Cards | ✅ Done | Bookmark icon with state |
| Save/Unsave Handlers | ✅ Done | In Jobs page with toast notifications |
| Saved Jobs Tab | ✅ Done | In Applications page with expiry countdown |

## Next Steps

1. **Run migration**: Execute [migrations/003_add_saved_jobs_feature.sql](migrations/003_add_saved_jobs_feature.sql) in Supabase SQL Editor
2. **Test end-to-end flow**: Save → View in Applications → Generate CV
3. **Verify scheduler**: Check logs to confirm cleanup job is scheduled
4. **Test 10 job limit**: Try saving more than 10 jobs

## Optional Enhancements (Future)

- [ ] Email notifications before job expiry (e.g., 2 days before)
- [ ] AI matcher boost based on saved job patterns
- [ ] Bulk actions (remove multiple saved jobs)
- [ ] Filter/sort saved jobs by date, expiry
- [ ] Export saved jobs list

---

**Completed**: 2026-01-10
**Backend Status**: ✅ Complete
**Frontend Status**: ✅ Complete
**Ready for Testing**: Yes
