# My External Jobs Page - User Guide

## 🎯 Overview
A dedicated page for managing all jobs you've manually added from LinkedIn, Indeed, company career pages, and other sources.

## 📍 Location
**Sidebar Navigation** → "My External Jobs" (3rd item, with a ⊕ icon)

## ✨ Features

### 1. **Quick Stats Dashboard**
At the top of the page, see at-a-glance:
- **Total Jobs** - How many external jobs you've added
- **Remote Jobs** - Jobs that offer remote work
- **This Week** - Jobs added in the last 7 days

### 2. **Job Cards**
Each job is displayed in a beautiful card showing:
- **Job Title & Company** with a company icon
- **Location, Salary, Job Type** (full-time, contract, etc.)
- **Remote/Hybrid indicators**
- **Experience Level** (entry, mid, senior)
- **Required Skills** (up to 6 shown, with "+" for more)
- **Top Requirements** (first 3 listed)
- **Link to Original Posting** (if available)

### 3. **Quick Actions**
Each job card has two buttons:
- **🔥 Generate CV** - Create a tailored CV and cover letter
- **👁️ View Details** - See full job description and requirements

### 4. **Add New Job Button**
Large orange button in the top-right corner to quickly add more jobs.

## 🚀 User Flow

### Adding Your First Job:
1. Navigate to **My External Jobs** in sidebar
2. Click **"Add Your First Job"** (or the orange button)
3. Paste a URL or job description
4. AI extracts all details automatically
5. Job appears in your list immediately

### Generating Materials:
1. Browse your external jobs
2. Click **"Generate CV"** on any job
3. Customize tone and settings
4. Download your tailored CV and cover letter

## 🎨 Design Highlights

- **Modern Card Layout** - Clean, spacious cards with hover effects
- **Color-Coded Tags** - Different colors for salary, remote, job type, etc.
- **Smooth Animations** - Cards fade in with staggered timing
- **Responsive** - Works perfectly on mobile, tablet, and desktop
- **Empty State** - Beautiful onboarding when no jobs exist yet

## 📊 What Gets Displayed

### Automatic AI Extraction:
- ✅ Job title
- ✅ Company name
- ✅ Location
- ✅ Salary range (min/max + currency)
- ✅ Job type (full-time, part-time, contract)
- ✅ Remote option (yes/no/hybrid)
- ✅ Experience level
- ✅ Required skills (parsed from job description)
- ✅ Requirements (key qualifications)
- ✅ Responsibilities (what you'll do)

### Visual Indicators:
- 💼 **Blue badges** - Job type
- 🌍 **Gray badges** - Location
- 💰 **Green badges** - Salary
- 🏠 **Purple badges** - Remote
- 📊 **Orange badges** - Experience level
- 🔧 **Turquoise badges** - Skills

## 🔗 Integration

This page integrates with:
- **Applications Page** - Generate CV flows to applications/generate
- **Jobs Page** - View details redirects to job detail page
- **Add External Job Modal** - Shared modal component for consistency

## ⚡ Performance

- Fetches only external jobs (filtered by source='external')
- Loads up to 100 jobs per page
- Fast rendering with React motion animations
- Optimized re-fetch on job add

## 🎯 Next Steps After Adding Jobs

1. **Generate CV** - Click the orange button to create tailored materials
2. **Save for Later** - Jobs stay in your list until you delete them
3. **View Details** - See full description and all requirements
4. **Track Applications** - After generating, track in Applications page

---

**Status**: ✅ Feature complete and ready to use!
