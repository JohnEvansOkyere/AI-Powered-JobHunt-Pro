# Job Search Guide

The job search page now has **two separate tabs** for different use cases:

## 1. Recommended for You Tab

**What it does:**
- Uses AI-powered matching with OpenAI embeddings
- Matches your **profile AND CV** to find the best job fits
- Shows jobs ranked by match score (60%+ quality matches only)
- No filters needed - purely based on your profile

**How matching works:**
1. Combines your profile data:
   - Primary and secondary job titles
   - Skills (technical + tools + soft skills)
   - Seniority level
   - Work preferences (remote/hybrid/onsite)
   - Desired industries
   - Experience from your CV
2. Creates semantic embedding using OpenAI
3. Compares against job embeddings
4. Returns only high-quality matches (60%+ relevance)

**Best for:**
- Finding jobs that match YOUR specific profile
- Discovering opportunities you might not have searched for
- Getting personalized recommendations

**What you see:**
- Match score percentage (e.g., "85% Match")
- Match reasons explaining why the job fits
- Jobs sorted by relevance (best matches first)

---

## 2. All Jobs Tab

**What it does:**
- Browse ALL available jobs in the database
- Apply filters to narrow down results
- Search by keywords, title, company

**Available filters:**
- Job Title
- Location
- Work Type (Remote/Hybrid/On-site)
- Seniority Level (Entry/Mid/Senior)
- Salary Range
- Date Posted

**Best for:**
- Exploring what's available
- Searching for specific job titles or companies
- Filtering by location, work type, or other criteria
- Finding jobs outside your primary profile

**What you see:**
- All jobs matching your search/filters
- No match scores (pure search results)
- Full filter sidebar for refinement

---

## When to Use Each Tab

### Use "Recommended for You" when:
- You want to see jobs that match your profile
- You're exploring what's available for someone with your skills
- You want AI to find the best matches for you
- You trust your profile is accurate and complete

### Use "All Jobs" when:
- You're looking for something specific (title, company, location)
- You want to explore beyond your primary profile
- You're searching for a specific role or industry
- You want full control over filtering

---

## Tips for Best Results

### For Recommendations:
1. **Complete your profile thoroughly**:
   - Add all relevant skills
   - Include both primary and secondary job titles
   - Set accurate work preferences
   - Upload an up-to-date CV

2. **The more complete your profile, the better the matches**

3. **Check recommendations regularly** - new matches are computed as new jobs are scraped

### For All Jobs:
1. **Use specific keywords** in the search bar
2. **Combine multiple filters** to narrow down results
3. **Try different search terms** if you don't find what you're looking for
4. **Check "Date Posted" filter** to see only recent jobs

---

## How Jobs Are Scraped

The platform automatically scrapes fresh tech jobs **every 3 days** from:
- **Remotive** (remote jobs)
- **RemoteOK** (remote jobs)

Categories scraped:
- Software Engineering (backend, frontend, full stack, mobile, DevOps)
- Data & AI (data scientist, ML engineer, AI engineer)
- Product & Design (product manager, UX/UI designer)
- Other Tech (cloud, security, QA, SRE)

**Expected volume:** 400-600 new jobs every 3 days

---

## Technical Details

### Recommendations Tab (AI Matching)
- **Technology**: OpenAI embeddings (text-embedding-3-small)
- **Data sources**: User profile + CV
- **Threshold**: 60% minimum match score
- **Sorting**: By relevance score (highest first)
- **Caching**: Matches are cached for performance

### All Jobs Tab (Direct Search)
- **Technology**: PostgreSQL full-text search
- **Data sources**: Job database
- **Filtering**: Real-time filtering on server
- **Sorting**: By posted date (newest first)
- **Pagination**: 20 jobs per page

---

## Troubleshooting

### No recommendations showing?
1. Make sure your profile is complete
2. Upload a CV with your experience
3. Wait for AI matching to compute (happens automatically)
4. Try the "All Jobs" tab to browse manually

### Recommendations not relevant?
1. Update your profile with accurate skills and preferences
2. Make sure your job titles reflect what you're looking for
3. Update your CV with current experience

### All Jobs tab not showing results?
1. Try broader search terms
2. Remove some filters
3. Check "Date Posted" - older jobs might have been archived
4. Wait for next scraping run (every 3 days)

---

## Future Enhancements

- Save favorite jobs
- Get email alerts for new matches
- Filter recommendations by work type/location
- Export job lists
- Track application status

---

**Enjoy exploring jobs! 🚀**
