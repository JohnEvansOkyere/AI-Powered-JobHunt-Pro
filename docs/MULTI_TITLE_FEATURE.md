# Multi-Title Job Search Feature

## Overview
Users can now add multiple job titles to their profile, allowing them to target various roles simultaneously. This improves job matching accuracy by considering all the roles a candidate is interested in.

## Features

### 1. **Multiple Job Title Input** ([components/profile/ProfileForm.tsx](../frontend/components/profile/ProfileForm.tsx))
- Users can add multiple job titles using a chip/tag interface
- Can enter multiple titles at once (comma-separated) or add them one at a time
- First title is automatically marked as "Primary"
- Visual chips show all titles with remove buttons
- Press Enter or click "Add" to add titles
- Duplicate titles are automatically filtered out

### 2. **Profile Display** ([app/dashboard/profile/page.tsx](../frontend/app/dashboard/profile/page.tsx))
- Shows all job titles with visual distinction:
  - Primary title: Highlighted in primary color with "(Primary)" label
  - Secondary titles: Displayed in neutral colors
- Clean, organized chip layout

### 3. **AI Job Matching Enhancement** ([backend/app/services/ai_job_matcher.py](../backend/app/services/ai_job_matcher.py))
- AI matcher now considers **all job titles** (primary + secondary) when:
  - Creating user profile embeddings for semantic matching
  - Generating match reasons
  - Checking title alignment

## How It Works

### Frontend
```typescript
// User adds titles: "Data Scientist", "ML Engineer", "AI Engineer"
{
  primary_job_title: "Data Scientist",
  secondary_job_titles: ["ML Engineer", "AI Engineer"]
}
```

### Backend (AI Matching)
```python
# Creates embedding with all titles
target_roles = []
if profile.primary_job_title:
    target_roles.append(profile.primary_job_title)
if profile.secondary_job_titles:
    target_roles.extend(profile.secondary_job_titles)

parts.append(f"Target roles: {', '.join(target_roles)}")
# Result: "Target roles: Data Scientist, ML Engineer, AI Engineer"
```

### Match Scoring
- AI will match jobs against **any** of the user's target roles
- If a job matches "Machine Learning Engineer", it will match both "ML Engineer" and "AI Engineer" titles
- Match reasons will show "Title aligns with your target roles" if any title matches

## User Experience

1. **Adding Titles:**
   - Navigate to Profile Setup → Career Targeting
   - Enter job titles in the input field (comma-separated or one at a time)
   - Click "Add" or press Enter
   - Titles appear as removable chips

2. **Viewing Profile:**
   - Navigate to Dashboard → Profile
   - See all job titles with primary/secondary distinction

3. **Job Matching:**
   - AI considers all titles when finding relevant jobs
   - Better match quality with multiple target roles
   - More accurate job recommendations

## Benefits

- **Broader Job Coverage**: Target multiple related roles simultaneously
- **Better Matching**: AI understands all your career interests
- **Flexibility**: Easily add/remove titles as career goals change
- **Clear Organization**: Primary vs secondary title distinction

## Technical Details

### Data Structure
- **primary_job_title**: String - First title added by user
- **secondary_job_titles**: Array of Strings - Additional titles

### Database Schema
Already supported in UserProfile model:
```python
primary_job_title = Column(Text, nullable=True)
secondary_job_titles = Column(ARRAY(Text), nullable=True)
```

### AI Matching Impact
- All titles included in user profile embedding
- Semantic matching considers all roles equally
- Match reasons check against all titles
- No performance impact (single embedding call)

## Example Use Cases

### 1. Career Transition
```
Primary: "Software Engineer"
Secondary: ["DevOps Engineer", "Cloud Engineer"]
```
→ Matches jobs in development and infrastructure

### 2. Specialized Roles
```
Primary: "Data Scientist"
Secondary: ["ML Engineer", "AI Engineer", "Research Scientist"]
```
→ Matches all ML/AI related positions

### 3. Leadership Roles
```
Primary: "Engineering Manager"
Secondary: ["Technical Lead", "Team Lead"]
```
→ Matches various leadership positions

## Future Enhancements

Potential improvements:
- [ ] Add priority levels to secondary titles
- [ ] Suggest related job titles based on skills
- [ ] Show match breakdown by title in job cards
- [ ] Allow reordering titles (change primary)

---

**Implementation Date**: December 2024
**Status**: ✅ Complete and tested
