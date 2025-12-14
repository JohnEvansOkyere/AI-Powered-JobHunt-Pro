# Phase 3: User Profile System ✅

## Overview

Phase 3 implemented a comprehensive user profile system with a multi-step form, full CRUD API endpoints, and complete profile management functionality. The profile system captures extensive user information for career targeting, skills, experience, preferences, and AI settings.

## Completed Components

### 1. Backend Profile API

**Location**: `backend/app/api/v1/endpoints/profiles.py`

#### Endpoints

1. **GET `/api/v1/profiles/me`**
   - Returns current user's profile
   - Response: `UserProfileResponse` with all profile data
   - Authentication: Required
   - Error: 404 if profile doesn't exist

2. **POST `/api/v1/profiles`**
   - Creates new user profile
   - Request: `UserProfileCreate` (all fields optional)
   - Response: `UserProfileResponse`
   - Authentication: Required
   - Error: 400 if profile already exists

3. **PUT `/api/v1/profiles`**
   - Updates existing profile
   - Request: `UserProfileUpdate` (all fields optional)
   - Response: `UserProfileResponse`
   - Authentication: Required
   - Error: 404 if profile doesn't exist

4. **DELETE `/api/v1/profiles`**
   - Deletes user profile
   - Response: 204 No Content
   - Authentication: Required
   - Error: 404 if profile doesn't exist

#### Data Models

**Pydantic Models**:

1. **`TechnicalSkill`**
   ```python
   {
     "skill": str,
     "years": int (optional),
     "confidence": int (1-5 scale)
   }
   ```

2. **`ExperienceItem`**
   ```python
   {
     "role": str,
     "company": str,
     "duration": str,
     "achievements": List[str],
     "metrics": Dict (optional)
   }
   ```

3. **`AIPreferences`**
   ```python
   {
     "job_matching": str (default: "gemini"),
     "cv_tailoring": str (default: "openai"),
     "cover_letter": str (default: "openai"),
     "email": str (default: "grok"),
     "speed_vs_quality": str ("speed" | "quality" | "balanced")
   }
   ```

4. **`UserProfileCreate`**: All profile fields (optional)
5. **`UserProfileUpdate`**: All profile fields (optional)
6. **`UserProfileResponse`**: Complete profile with metadata

#### Profile Fields Structure

**Career Targeting**:
- Primary job title
- Secondary job titles (array)
- Seniority level (entry, mid, senior, lead, executive)
- Desired industries (array)
- Company size preference
- Salary range (min/max)
- Contract type (array: full-time, contract, freelance, part-time)
- Work preference (remote, hybrid, onsite, flexible)

**Skills & Tools**:
- Technical skills (JSONB: skill, years, confidence)
- Soft skills (array)
- Tools and technologies (array)

**Experience**:
- Experience items (JSONB: role, company, duration, achievements, metrics)

**Job Filtering Preferences**:
- Preferred keywords (array)
- Excluded keywords (array)
- Blacklisted companies (array)
- Job boards to include/exclude (arrays)
- Job freshness window (days)

**Application Style**:
- Writing tone (formal, friendly, confident, professional)
- Personal branding summary
- First-person vs third-person
- Email length preference (short, medium, long)

**Language & Localization**:
- Preferred language
- Local job market focus

**AI Preferences**:
- Model selection per task
- Speed vs quality preference

### 2. Frontend Profile Management

#### TypeScript Types

**Location**: `frontend/types/profile.ts`

Complete TypeScript interfaces matching backend models:
- `TechnicalSkill`
- `ExperienceItem`
- `AIPreferences`
- `UserProfile`
- `UserProfileFormData`

#### API Client Functions

**Location**: `frontend/lib/api/profiles.ts`

1. **`getMyProfile()`**: Fetch current user's profile
2. **`createProfile(data)`**: Create new profile
3. **`updateProfile(data)`**: Update existing profile
4. **`deleteProfile()`**: Delete profile

All functions are type-safe and handle errors.

#### useProfile Hook

**Location**: `frontend/hooks/useProfile.ts`

**Features**:
- Profile state management
- Automatic profile loading
- Save functionality (create or update)
- Loading and saving states
- Error handling with toast notifications

**Returns**:
```typescript
{
  profile: UserProfile | null
  loading: boolean
  saving: boolean
  hasProfile: boolean
  loadProfile: () => Promise<void>
  saveProfile: (data: UserProfileFormData) => Promise<UserProfile>
}
```

**Usage**:
```typescript
const { profile, loading, saveProfile } = useProfile()
```

### 3. Multi-Step Profile Form

**Location**: `frontend/components/profile/ProfileForm.tsx`

#### Form Structure

**6 Steps**:

1. **Career Targeting**
   - Primary job title
   - Secondary job titles
   - Seniority level
   - Desired industries
   - Company size preference
   - Salary range
   - Contract type
   - Work preference

2. **Skills & Tools**
   - Technical skills (with years and confidence)
   - Soft skills
   - Tools and technologies

3. **Work Experience**
   - Role, company, duration
   - Achievements (bullet points)
   - Impact metrics

4. **Job Preferences**
   - Preferred keywords
   - Excluded keywords
   - Blacklisted companies
   - Job boards preferences
   - Job freshness window

5. **Application Style**
   - Writing tone
   - Personal branding summary
   - First-person preference
   - Email length preference

6. **AI Preferences**
   - Model selection per task
   - Speed vs quality preference

#### Form Features

- **Progress Bar**: Visual progress indicator
- **Step Navigation**: Previous/Next buttons
- **Form Validation**: Client-side validation
- **Auto-save Ready**: Can be extended for auto-save
- **Responsive Design**: Mobile-friendly
- **Loading States**: Saving indicator
- **Error Handling**: Toast notifications

### 4. Profile Setup Page

**Location**: `frontend/app/profile/setup/page.tsx`

**Features**:
- Protected route (requires authentication)
- Profile form integration
- Completion callback (redirects to dashboard)
- Loading state handling
- Clean, centered layout

### 5. Dashboard Integration

**Location**: `frontend/app/dashboard/page.tsx`

**Enhanced Features**:
- **Profile Check**: Automatically checks if profile exists
- **Auto-redirect**: Redirects to profile setup if no profile
- **Profile Summary Cards**: Shows key profile information
- **Quick Actions**: Links to profile editing and future features
- **Welcome Message**: Personalized with job title

**Profile Summary Cards**:
- Job Title
- Seniority Level
- Work Preference

**Quick Actions**:
- Edit Profile
- Upload CV (coming soon)
- Find Jobs (coming soon)
- My Applications (coming soon)

## Data Flow

### Profile Creation Flow

1. User completes multi-step form
2. Form data collected in state
3. User clicks "Complete Profile"
4. `saveProfile()` called with form data
5. API request to `POST /api/v1/profiles`
6. Backend validates and stores in database
7. Profile returned and stored in state
8. User redirected to dashboard

### Profile Update Flow

1. User navigates to profile setup
2. Existing profile loaded via `useProfile()`
3. Form pre-filled with existing data
4. User makes changes
5. `saveProfile()` called with updated data
6. API request to `PUT /api/v1/profiles`
7. Backend updates database
8. Updated profile returned
9. Success notification shown

## Database Integration

### UserProfile Model

**Location**: `backend/app/models/user_profile.py`

- **SQLAlchemy Model**: Maps to `user_profiles` table
- **JSONB Fields**: Technical skills, experience, AI preferences
- **Array Fields**: Secondary titles, industries, skills, etc.
- **Constraints**: Check constraints for enums
- **Timestamps**: Automatic created_at/updated_at

### Database Schema

**Table**: `user_profiles`

- **Primary Key**: `id` (UUID)
- **Foreign Key**: `user_id` → `auth.users(id)`
- **Unique Constraint**: One profile per user
- **Indexes**: On user_id, primary_job_title, technical_skills
- **RLS Policies**: Users can only access their own profile

## API Integration

### Authentication

All profile endpoints require:
- Valid JWT token in `Authorization: Bearer <token>` header
- Token verified via `get_current_user` dependency
- User ID extracted from token

### Error Handling

**Backend**:
- 401: Unauthorized (invalid token)
- 404: Profile not found
- 400: Bad request (validation errors)
- 500: Server errors

**Frontend**:
- Toast notifications for errors
- Loading states
- Graceful error handling

## Form Validation

### Client-Side
- Required field validation
- Type validation (numbers, arrays)
- Format validation (email, URLs)
- Range validation (confidence 1-5)

### Server-Side
- Pydantic model validation
- Database constraint validation
- Type coercion
- Enum validation

## UI/UX Features

✅ **Progress Indicator**: Visual progress bar
✅ **Step Navigation**: Clear previous/next buttons
✅ **Form Validation**: Real-time validation feedback
✅ **Loading States**: Saving indicators
✅ **Error Messages**: Clear, actionable errors
✅ **Responsive Design**: Mobile-friendly
✅ **Accessibility**: ARIA labels, keyboard navigation
✅ **Toast Notifications**: Success/error feedback

## Testing Checklist

✅ Create new profile
✅ Update existing profile
✅ View profile in dashboard
✅ Multi-step form navigation
✅ Form validation
✅ Error handling
✅ Loading states
✅ Auto-redirect if no profile
✅ Profile summary display

## Data Structure Examples

### Technical Skills
```json
[
  {
    "skill": "Python",
    "years": 5,
    "confidence": 5
  },
  {
    "skill": "React",
    "years": 3,
    "confidence": 4
  }
]
```

### Experience
```json
[
  {
    "role": "Senior Software Engineer",
    "company": "Tech Corp",
    "duration": "2020-2023",
    "achievements": [
      "Led team of 5 developers",
      "Increased performance by 40%"
    ],
    "metrics": {
      "team_size": 5,
      "performance_improvement": 40
    }
  }
]
```

### AI Preferences
```json
{
  "job_matching": "gemini",
  "cv_tailoring": "openai",
  "cover_letter": "openai",
  "email": "grok",
  "speed_vs_quality": "balanced"
}
```

## Next Phase

Phase 4: CV Management
- CV upload functionality
- CV parsing and extraction
- CV preview and management
- Structured data extraction

## Notes

- **JSONB Storage**: Complex data stored as JSONB for flexibility
- **Partial Updates**: PUT endpoint supports partial updates
- **Type Safety**: Full TypeScript coverage
- **Scalability**: Designed to handle large profiles
- **Extensibility**: Easy to add new profile fields

