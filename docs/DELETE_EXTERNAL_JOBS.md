# Delete External Jobs Feature

## Overview
Added the ability for users to delete external jobs they've manually added to the platform.

## Security & Permissions
The delete functionality includes important safeguards:

### Backend Validation (`/backend/app/api/v1/endpoints/jobs.py`)
```python
@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id, current_user, db):
    """
    Delete a job posting.
    Only allows deletion of external jobs added by the current user.
    """
```

**Security Checks:**
1. ✅ **Authentication Required**: User must be logged in (`get_current_user` dependency)
2. ✅ **Job Must Exist**: Returns 404 if job not found
3. ✅ **External Jobs Only**: Returns 403 if trying to delete scraped jobs (only `source='external'` allowed)
4. ✅ **Owner Verification**: Returns 403 if job was not added by the current user
5. ✅ **Cascading Delete**: Automatically removes all applications before deleting the job
6. ✅ **Transaction Safety**: Rolls back on error to maintain data integrity
7. ✅ **Audit Logging**: Logs deletion with user ID, job ID, and count of deleted applications

## Implementation Details

### Backend (`/backend/app/api/v1/endpoints/jobs.py`)
- **Endpoint**: `DELETE /api/v1/jobs/{job_id}`
- **Status Code**: 204 No Content (success)
- **Authentication**: Required via JWT token
- **Permissions**: Users can only delete external jobs they added
- **Cascading Delete**: Automatically deletes all associated applications, CVs, and cover letters
- **Transaction Safety**: Wrapped in try-catch with rollback on failure

### Frontend API (`/frontend/lib/api/jobs.ts`)
```typescript
export async function deleteJob(jobId: string): Promise<void> {
  return apiClient.delete(`/api/v1/jobs/${jobId}`) as Promise<void>
}
```

### UI Component (`/frontend/app/dashboard/external-jobs/page.tsx`)

#### Features:
1. **Delete Button**:
   - Red-colored button with trash icon
   - Located in action buttons column alongside "Generate CV" and "View Details"
   - Shows loading state during deletion

2. **Confirmation Dialog**:
   - Native browser confirmation prompt
   - Displays job title in confirmation message
   - **Warns about cascading deletion** of CVs and cover letters
   - Multi-line message for clarity:
     - "Are you sure you want to delete \"{jobTitle}\"?"
     - "This will also delete any generated CVs and cover letters for this job."
     - "This action cannot be undone."

3. **Loading State**:
   - Button disabled during deletion
   - Shows spinner and "Deleting..." text
   - Prevents multiple delete requests

4. **Success/Error Handling**:
   - Success: Toast notification "Job and associated materials deleted successfully" + job removed from list instantly (no reload needed)
   - Error: Toast error with message + button re-enabled

## User Flow

1. User navigates to "My External Jobs" page
2. User clicks red "Delete" button on a job card
3. **Enhanced confirmation dialog** appears:
   - Shows job title
   - **Warns that associated CVs and cover letters will also be deleted**
   - States action is irreversible
4. User confirms deletion
5. Button shows loading state ("Deleting...")
6. **Backend deletes:**
   - All generated applications (CVs, cover letters) for this job
   - The job posting itself
7. Success toast: "Job and associated materials deleted successfully"
8. Job card disappears from list (instant UI update)

## What Gets Deleted

When you delete an external job, the following are **permanently removed**:

1. ✅ The job posting
2. ✅ All generated tailored CVs for this job
3. ✅ All generated cover letters for this job
4. ✅ All application materials and metadata

**⚠️ Important**: This is a cascading delete operation that removes all related data.

## Design Details

### Button Styling
```tsx
<button
  onClick={() => handleDeleteJob(job.id, job.title)}
  disabled={deletingJobId === job.id}
  className="flex-1 lg:w-full px-6 py-4 bg-red-50 text-red-600 rounded-2xl font-bold text-sm hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
>
  {deletingJobId === job.id ? (
    <>
      <Loader2 className="w-5 h-5 animate-spin" />
      <span>Deleting...</span>
    </>
  ) : (
    <>
      <Trash2 className="w-5 h-5" />
      <span>Delete</span>
    </>
  )}
</button>
```

- **Normal State**: Light red background (`bg-red-50`), red text (`text-red-600`)
- **Hover State**: Darker red background (`hover:bg-red-100`)
- **Disabled State**: 50% opacity, cursor not-allowed
- **Loading State**: Animated spinner icon

## What Cannot Be Deleted

For data integrity and security reasons, the following jobs **cannot** be deleted:
- ❌ Jobs scraped from job boards (Indeed, LinkedIn, RemoteOK, etc.)
- ❌ Jobs from automated scrapers
- ❌ Jobs added by other users
- ❌ Jobs with `source != 'external'`

**Attempting to delete these will return:**
```json
{
  "detail": "Can only delete external jobs that you added"
}
```

## Testing Checklist

### Functional Tests
- [ ] Can delete own external job successfully
- [ ] **Deleting job also deletes all associated applications/CVs**
- [ ] Cannot delete jobs added by other users (403 error)
- [ ] Cannot delete scraped jobs (403 error)
- [ ] Confirmation dialog shows correct job title and warning about CVs
- [ ] Job disappears from list after deletion
- [ ] Toast success message mentions "associated materials"
- [ ] Delete button shows loading state during deletion
- [ ] Cannot double-click delete button (disabled during deletion)
- [ ] **Database rollback works if deletion fails mid-transaction**

### Edge Cases
- [ ] Attempting to delete non-existent job returns 404
- [ ] Network error shows error toast
- [ ] Backend validation errors are displayed to user
- [ ] Stats counters update after deletion (total jobs, remote jobs, this week)

### UI/UX Tests
- [ ] Delete button is clearly visible and styled as destructive action
- [ ] Loading spinner displays during deletion
- [ ] Button remains disabled until operation completes
- [ ] Confirmation dialog text is clear and informative
- [ ] No page reload required after deletion

## API Documentation

### DELETE /api/v1/jobs/{job_id}

**Description**: Delete an external job posting

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:
- `job_id` (UUID, required): The ID of the job to delete

**Response Codes**:
- `204 No Content`: Job successfully deleted
- `401 Unauthorized`: User not authenticated
- `403 Forbidden`: User cannot delete this job (not owner or not external)
- `404 Not Found`: Job does not exist

**Example Request**:
```bash
DELETE /api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <jwt_token>
```

**Example Error Responses**:

Job not found:
```json
{
  "detail": "Job not found"
}
```

Cannot delete scraped job:
```json
{
  "detail": "Can only delete external jobs that you added"
}
```

Not the job owner:
```json
{
  "detail": "You can only delete jobs that you added"
}
```

## Future Enhancements

Potential improvements for future iterations:

1. **Soft Delete**: Archive jobs instead of hard delete (keep in DB with `deleted_at` timestamp)
2. **Bulk Delete**: Select multiple jobs and delete at once
3. **Undo Feature**: Toast notification with "Undo" button for 5 seconds
4. **Delete from Details Page**: Add delete button on job details page too
5. **Confirmation Modal**: Custom modal instead of browser confirm dialog
6. **Analytics**: Track deletion patterns (why users delete jobs)

## Files Modified

### Backend
- `/backend/app/api/v1/endpoints/jobs.py` - Added `DELETE /{job_id}` endpoint

### Frontend
- `/frontend/lib/api/jobs.ts` - Added `deleteJob()` function
- `/frontend/app/dashboard/external-jobs/page.tsx` - Added delete button and handler

## Related Features
- [External Job Parser](./EXTERNAL_JOB_PARSER.md)
- [External Jobs Page](./EXTERNAL_JOBS_PAGE_GUIDE.md)
- [AI CV Generation](./AI_CV_GENERATOR_GUIDE.md)
