-- =====================================================
-- AI-Powered Job Application Platform
-- Complete Supabase Database Setup
-- =====================================================
--
-- This file contains all necessary SQL scripts to set up
-- the complete database schema, RLS policies, triggers,
-- and storage policies for the AI-Powered Job Hunt Pro platform.
--
-- Run this script in Supabase SQL Editor to set up everything.
-- =====================================================

-- =====================================================
-- PART 1: EXTENSIONS
-- =====================================================

-- Enable necessary PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search

-- =====================================================
-- PART 2: PUBLIC USERS TABLE
-- =====================================================
-- Extends auth.users with additional user metadata

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

    -- User Information
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,

    -- Account Status
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,

    -- Metadata
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Additional metadata (flexible JSONB field)
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users(is_active);

-- =====================================================
-- PART 3: USER PROFILES TABLE
-- =====================================================
-- Stores comprehensive user profile information

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Career Targeting
    primary_job_title TEXT,
    secondary_job_titles TEXT[], -- Array of job titles
    seniority_level TEXT CHECK (seniority_level IN ('entry', 'mid', 'senior', 'lead', 'executive')),
    desired_industries TEXT[],
    company_size_preference TEXT CHECK (company_size_preference IN ('startup', 'small', 'medium', 'large', 'enterprise', 'any')),
    salary_range_min INTEGER,
    salary_range_max INTEGER,
    contract_type TEXT[] CHECK (contract_type <@ ARRAY['full-time', 'contract', 'freelance', 'part-time']),
    work_preference TEXT CHECK (work_preference IN ('remote', 'hybrid', 'onsite', 'flexible')),

    -- Skills & Tools
    technical_skills JSONB, -- [{skill: string, years: int, confidence: int}]
    soft_skills TEXT[],
    tools_technologies TEXT[],

    -- Experience Breakdown
    experience JSONB, -- [{role: string, company: string, duration: string, achievements: string[], metrics: jsonb}]

    -- Job Filtering Preferences
    preferred_keywords TEXT[],
    excluded_keywords TEXT[],
    blacklisted_companies TEXT[],
    job_boards_include TEXT[],
    job_boards_exclude TEXT[],
    job_freshness_days INTEGER DEFAULT 30,

    -- Application Style
    writing_tone TEXT CHECK (writing_tone IN ('formal', 'friendly', 'confident', 'professional')),
    personal_branding_summary TEXT,
    first_person BOOLEAN DEFAULT true,
    email_length_preference TEXT CHECK (email_length_preference IN ('short', 'medium', 'long')),

    -- Language & Localization
    preferred_language TEXT DEFAULT 'en',
    local_job_market TEXT,

    -- AI Preferences
    ai_preferences JSONB, -- {job_matching: string, cv_tailoring: string, cover_letter: string, email: string, speed_vs_quality: string}

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id)
);

-- Indexes for user_profiles
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_primary_job_title ON user_profiles USING gin(primary_job_title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_user_profiles_technical_skills ON user_profiles USING gin(technical_skills);

-- =====================================================
-- PART 4: CVS TABLE
-- =====================================================
-- Stores CV metadata and parsed content

CREATE TABLE IF NOT EXISTS cvs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- File Information
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL, -- Supabase Storage path
    file_size INTEGER, -- Size in bytes
    file_type TEXT, -- 'pdf' or 'docx'
    mime_type TEXT,

    -- Parsed Content
    parsed_content JSONB, -- Structured data extracted from CV
    raw_text TEXT, -- Full text content

    -- Status
    parsing_status TEXT DEFAULT 'pending' CHECK (parsing_status IN ('pending', 'processing', 'completed', 'failed')),
    parsing_error TEXT,

    -- Metadata
    is_active BOOLEAN DEFAULT true, -- Only one active CV per user
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for cvs
CREATE INDEX IF NOT EXISTS idx_cvs_user_id ON cvs(user_id);
CREATE INDEX IF NOT EXISTS idx_cvs_user_id_active ON cvs(user_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_cvs_parsing_status ON cvs(parsing_status);

-- =====================================================
-- PART 5: JOBS TABLE
-- =====================================================
-- Stores scraped job listings

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Job Information
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    description TEXT NOT NULL,
    job_link TEXT NOT NULL UNIQUE,

    -- Source Information
    source TEXT NOT NULL, -- 'linkedin', 'indeed', 'glassdoor', etc.
    source_id TEXT, -- ID from the source platform
    posted_date TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Normalized Data
    normalized_title TEXT,
    normalized_location TEXT,
    salary_range TEXT,
    job_type TEXT, -- 'full-time', 'contract', etc.
    remote_type TEXT, -- 'remote', 'hybrid', 'onsite'

    -- Processing Status
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processed', 'archived')),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for jobs
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_date ON jobs(posted_date DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_processing_status ON jobs(processing_status);
CREATE INDEX IF NOT EXISTS idx_jobs_title_company ON jobs USING gin(title gin_trgm_ops, company gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_job_link ON jobs(job_link);

-- =====================================================
-- PART 6: JOB MATCHES TABLE
-- =====================================================
-- Stores job matching results for users

CREATE TABLE IF NOT EXISTS job_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,

    -- Matching Scores
    relevance_score DECIMAL(5, 2) NOT NULL, -- 0.00 to 100.00
    skill_match_score DECIMAL(5, 2),
    experience_match_score DECIMAL(5, 2),
    preference_match_score DECIMAL(5, 2),

    -- Match Details
    match_reasons JSONB, -- Array of reasons why this job matches
    matched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- User Actions
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'viewed', 'applied', 'saved', 'dismissed')),
    user_notes TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, job_id)
);

-- Indexes for job_matches
CREATE INDEX IF NOT EXISTS idx_job_matches_user_id ON job_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_job_id ON job_matches(job_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_relevance_score ON job_matches(relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_job_matches_user_status ON job_matches(user_id, status);

-- =====================================================
-- PART 7: APPLICATIONS TABLE
-- =====================================================
-- Stores generated application materials

CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    cv_id UUID REFERENCES cvs(id) ON DELETE SET NULL,

    -- Generated Materials
    tailored_cv_path TEXT, -- Path to generated CV in storage
    cover_letter TEXT,
    application_email TEXT,

    -- Generation Metadata
    ai_model_used TEXT, -- Which AI model was used
    generation_prompt TEXT, -- Prompt used for generation
    generation_settings JSONB, -- Settings used (tone, length, etc.)

    -- Status
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'reviewed', 'finalized', 'sent')),

    -- User Customizations
    user_edits JSONB, -- User modifications to generated content

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for applications
CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);

-- =====================================================
-- PART 8: SCRAPING JOBS TABLE
-- =====================================================
-- Tracks background scraping jobs

CREATE TABLE IF NOT EXISTS scraping_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Job Configuration
    sources TEXT[] NOT NULL, -- Which job boards to scrape
    keywords TEXT[],
    filters JSONB, -- Additional filters

    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    progress INTEGER DEFAULT 0, -- 0-100
    jobs_found INTEGER DEFAULT 0,
    jobs_processed INTEGER DEFAULT 0,

    -- Results
    error_message TEXT,
    result_summary JSONB,

    -- Metadata
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for scraping_jobs
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_user_id ON scraping_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_status ON scraping_jobs(status);

-- =====================================================
-- PART 9: ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE cvs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraping_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Users Table Policies
CREATE POLICY "Users can view own profile"
    ON public.users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

-- User Profiles Policies
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id);

-- CVs Policies
CREATE POLICY "Users can view own CVs"
    ON cvs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own CVs"
    ON cvs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own CVs"
    ON cvs FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own CVs"
    ON cvs FOR DELETE
    USING (auth.uid() = user_id);

-- Job Matches Policies
CREATE POLICY "Users can view own job matches"
    ON job_matches FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own job matches"
    ON job_matches FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own job matches"
    ON job_matches FOR UPDATE
    USING (auth.uid() = user_id);

-- Applications Policies
CREATE POLICY "Users can view own applications"
    ON applications FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own applications"
    ON applications FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own applications"
    ON applications FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own applications"
    ON applications FOR DELETE
    USING (auth.uid() = user_id);

-- Scraping Jobs Policies
CREATE POLICY "Users can view own scraping jobs"
    ON scraping_jobs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own scraping jobs"
    ON scraping_jobs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Jobs Policies (Public read for authenticated users)
CREATE POLICY "Authenticated users can view jobs"
    ON jobs FOR SELECT
    USING (auth.role() = 'authenticated');

-- =====================================================
-- PART 10: FUNCTIONS & TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp (generic)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Triggers for updated_at on all tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cvs_updated_at BEFORE UPDATE ON cvs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_matches_updated_at BEFORE UPDATE ON job_matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to ensure only one active CV per user
CREATE OR REPLACE FUNCTION ensure_single_active_cv()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = true THEN
        UPDATE cvs
        SET is_active = false
        WHERE user_id = NEW.user_id
        AND id != NEW.id
        AND is_active = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER ensure_single_active_cv_trigger
    BEFORE INSERT OR UPDATE ON cvs
    FOR EACH ROW
    WHEN (NEW.is_active = true)
    EXECUTE FUNCTION ensure_single_active_cv();

-- Function to sync user data from auth.users to public.users
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, email_verified, metadata)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        COALESCE(NEW.raw_user_meta_data, '{}'::jsonb)
    )
    ON CONFLICT (id) DO UPDATE
    SET
        email = EXCLUDED.email,
        email_verified = COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        metadata = COALESCE(NEW.raw_user_meta_data, '{}'::jsonb),
        updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to sync when user is created/updated in auth.users
CREATE TRIGGER on_auth_user_created_sync
    AFTER INSERT OR UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_auth_user();

-- Function to create user profile when user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-create user profile on signup
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- =====================================================
-- PART 11: STORAGE POLICIES (for 'cvs' bucket)
-- =====================================================
-- Note: Create the 'cvs' storage bucket in Supabase Dashboard first
-- Then run these policies in SQL Editor

-- Policy: Users can upload their own CVs
-- Files are stored as: {user_id}/{cv_id}.{ext}
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

-- =====================================================
-- PART 12: SYNC EXISTING DATA (Optional)
-- =====================================================
-- Run these if you have existing users without profiles/records

-- Sync existing auth.users to public.users
INSERT INTO public.users (id, email, email_verified, metadata)
SELECT
    id,
    email,
    COALESCE(email_confirmed_at IS NOT NULL, false) as email_verified,
    COALESCE(raw_user_meta_data, '{}'::jsonb) as metadata
FROM auth.users
WHERE id NOT IN (SELECT id FROM public.users)
ON CONFLICT (id) DO NOTHING;

-- Create profiles for existing users without profiles
INSERT INTO public.user_profiles (user_id)
SELECT id FROM auth.users
WHERE id NOT IN (SELECT user_id FROM public.user_profiles)
ON CONFLICT (user_id) DO NOTHING;

-- =====================================================
-- SETUP COMPLETE!
-- =====================================================
-- Your database is now fully configured with:
-- ✅ All tables with proper constraints and indexes
-- ✅ Row Level Security (RLS) policies
-- ✅ Automated triggers for data integrity
-- ✅ Auto-profile creation on user signup
-- ✅ Storage policies for CV management
--
-- Next steps:
-- 1. Create the 'cvs' storage bucket in Supabase Dashboard
-- 2. Verify all tables are created: Check "Table Editor" in Supabase
-- 3. Test RLS policies: Try accessing data as different users
-- 4. Start your backend server and test API endpoints
-- =====================================================
