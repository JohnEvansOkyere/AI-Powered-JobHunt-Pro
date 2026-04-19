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
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- For gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search
CREATE EXTENSION IF NOT EXISTS "vector"; -- Recommendations V2 embeddings

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

-- Sync existing Supabase Auth users early so later public.users FKs can validate.
INSERT INTO public.users (id, email, email_verified, metadata)
SELECT
    id,
    email,
    COALESCE(email_confirmed_at IS NOT NULL, false) as email_verified,
    COALESCE(raw_user_meta_data, '{}'::jsonb) as metadata
FROM auth.users
WHERE id NOT IN (SELECT id FROM public.users)
ON CONFLICT (id) DO NOTHING;

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
    ai_preferences JSONB, -- {job_matching: string, email: string, speed_vs_quality: string}

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
    job_link TEXT,

    -- Source Information
    source TEXT NOT NULL, -- 'linkedin', 'indeed', 'glassdoor', etc.
    source_id TEXT, -- ID from the source platform
    source_url TEXT, -- Original URL for external/user-added jobs
    posted_date TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    added_by_user_id UUID,

    -- Normalized Data
    normalized_title TEXT,
    normalized_location TEXT,
    salary_range TEXT,
    salary_min TEXT,
    salary_max TEXT,
    salary_currency VARCHAR(10),
    job_type TEXT, -- 'full-time', 'contract', etc.
    remote_type TEXT, -- 'remote', 'hybrid', 'onsite'
    remote_option VARCHAR(10),
    experience_level VARCHAR(20),
    requirements TEXT,
    responsibilities TEXT,
    skills TEXT,

    -- Processing Status
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processed', 'archived')),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Existing installs may have the pre-external-jobs schema; keep this setup
-- file safe to rerun by aligning those columns explicitly.
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_link_key;
ALTER TABLE jobs ALTER COLUMN job_link DROP NOT NULL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS added_by_user_id UUID;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_min TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_max TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_currency VARCHAR(10);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS remote_option VARCHAR(10);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS experience_level VARCHAR(20);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS requirements TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS responsibilities TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skills TEXT;

-- Indexes for jobs
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_date ON jobs(posted_date DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_processing_status ON jobs(processing_status);
DROP INDEX IF EXISTS idx_jobs_title_company;
CREATE INDEX IF NOT EXISTS idx_jobs_title_trgm ON jobs USING gin(title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_company_trgm ON jobs USING gin(company gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_title_company ON jobs(title, company);
CREATE INDEX IF NOT EXISTS idx_jobs_job_link ON jobs(job_link);
CREATE INDEX IF NOT EXISTS idx_jobs_added_by_user_id ON jobs(added_by_user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_source_url ON jobs(source_url);
CREATE INDEX IF NOT EXISTS idx_jobs_experience_level ON jobs(experience_level);

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
-- Tracks a candidate's relationship with a job

CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    cv_id UUID REFERENCES cvs(id) ON DELETE SET NULL,

    -- Status
    status TEXT DEFAULT 'saved'
        CHECK (status IN ('saved', 'applied', 'dismissed', 'hidden', 'interviewing', 'rejected', 'offer')),

    -- Saved-job retention
    saved_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Existing installs may have the removed CV-tailoring columns/statuses.
ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_status_check;
UPDATE applications SET status = 'saved'
WHERE status IN ('draft', 'reviewed', 'finalized', 'sent');
UPDATE applications SET status = 'applied'
WHERE status = 'submitted';
UPDATE applications SET status = 'saved'
WHERE status IS NULL
   OR status NOT IN ('saved', 'applied', 'dismissed', 'hidden', 'interviewing', 'rejected', 'offer');

ALTER TABLE applications DROP COLUMN IF EXISTS tailored_cv_path;
ALTER TABLE applications DROP COLUMN IF EXISTS cover_letter;
ALTER TABLE applications DROP COLUMN IF EXISTS application_email;
ALTER TABLE applications DROP COLUMN IF EXISTS ai_model_used;
ALTER TABLE applications DROP COLUMN IF EXISTS generation_prompt;
ALTER TABLE applications DROP COLUMN IF EXISTS generation_settings;
ALTER TABLE applications DROP COLUMN IF EXISTS user_edits;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS saved_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE applications
    ADD CONSTRAINT applications_status_check
    CHECK (status IN ('saved', 'applied', 'dismissed', 'hidden', 'interviewing', 'rejected', 'offer'));
ALTER TABLE applications ALTER COLUMN status SET DEFAULT 'saved';

-- Indexes for applications
CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_expires_at ON applications(expires_at);

-- =====================================================
-- PART 8: JOB RECOMMENDATIONS + EMBEDDINGS
-- =====================================================
-- Stores precomputed tiered recommendations and cached vectors.

CREATE TABLE IF NOT EXISTS job_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,

    -- Composite ordering score, 0.0-1.0
    match_score DOUBLE PRECISION NOT NULL,
    match_reason TEXT,

    -- Recommendations V2 scoring details
    tier TEXT NOT NULL DEFAULT 'tier2'
        CHECK (tier IN ('tier1', 'tier2', 'tier3')),
    semantic_fit DOUBLE PRECISION,
    title_alignment DOUBLE PRECISION,
    skill_overlap DOUBLE PRECISION,
    freshness DOUBLE PRECISION,
    channel_bonus DOUBLE PRECISION,
    interest_affinity DOUBLE PRECISION,
    llm_rerank_score DOUBLE PRECISION,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    CONSTRAINT unique_user_job_recommendation UNIQUE(user_id, job_id)
);

ALTER TABLE job_recommendations ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'tier2';
ALTER TABLE job_recommendations ADD COLUMN IF NOT EXISTS semantic_fit DOUBLE PRECISION;
ALTER TABLE job_recommendations ADD COLUMN IF NOT EXISTS title_alignment DOUBLE PRECISION;
ALTER TABLE job_recommendations ADD COLUMN IF NOT EXISTS skill_overlap DOUBLE PRECISION;
ALTER TABLE job_recommendations ADD COLUMN IF NOT EXISTS freshness DOUBLE PRECISION;
ALTER TABLE job_recommendations ADD COLUMN IF NOT EXISTS channel_bonus DOUBLE PRECISION;
ALTER TABLE job_recommendations ADD COLUMN IF NOT EXISTS interest_affinity DOUBLE PRECISION;
ALTER TABLE job_recommendations ADD COLUMN IF NOT EXISTS llm_rerank_score DOUBLE PRECISION;
ALTER TABLE job_recommendations ALTER COLUMN tier SET DEFAULT 'tier2';
UPDATE job_recommendations SET tier = 'tier2' WHERE tier IS NULL;
ALTER TABLE job_recommendations ALTER COLUMN tier SET NOT NULL;
ALTER TABLE job_recommendations DROP CONSTRAINT IF EXISTS job_recommendations_tier_check;
ALTER TABLE job_recommendations
    ADD CONSTRAINT job_recommendations_tier_check
    CHECK (tier IN ('tier1', 'tier2', 'tier3'));

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_job_recommendations_user_id'
    ) THEN
        BEGIN
            ALTER TABLE job_recommendations
                ADD CONSTRAINT fk_job_recommendations_user_id
                FOREIGN KEY (user_id)
                REFERENCES public.users(id)
                ON DELETE CASCADE
                NOT VALID;

            ALTER TABLE job_recommendations
                VALIDATE CONSTRAINT fk_job_recommendations_user_id;
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'Could not add fk_job_recommendations_user_id: %', SQLERRM;
        END;
    END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_recommendations_user_expires
    ON job_recommendations(user_id, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommendations_score
    ON job_recommendations(user_id, match_score DESC);
CREATE INDEX IF NOT EXISTS idx_recommendations_expires
    ON job_recommendations(expires_at);
CREATE INDEX IF NOT EXISTS idx_recommendations_user_tier_score
    ON job_recommendations(user_id, tier, match_score DESC);

CREATE TABLE IF NOT EXISTS job_embeddings (
    job_id UUID PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    model TEXT NOT NULL DEFAULT 'gemini-embedding-001',
    source_hash TEXT NOT NULL,
    embedded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
ALTER TABLE job_embeddings ALTER COLUMN model SET DEFAULT 'gemini-embedding-001';

CREATE INDEX IF NOT EXISTS idx_job_embeddings_hnsw
    ON job_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_job_embeddings_model
    ON job_embeddings(model);

CREATE TABLE IF NOT EXISTS user_embeddings (
    user_id UUID PRIMARY KEY,
    embedding vector(768) NOT NULL,
    model TEXT NOT NULL DEFAULT 'gemini-embedding-001',
    source_hash TEXT NOT NULL,
    embedded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
ALTER TABLE user_embeddings ALTER COLUMN model SET DEFAULT 'gemini-embedding-001';

CREATE INDEX IF NOT EXISTS idx_user_embeddings_model
    ON user_embeddings(model);

-- =====================================================
-- PART 9: WHATSAPP NOTIFICATIONS
-- =====================================================
-- Stores opt-in preferences and WhatsApp delivery audit records.

CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    whatsapp_opted_in BOOLEAN NOT NULL DEFAULT FALSE,
    whatsapp_opted_in_at TIMESTAMP WITH TIME ZONE,
    whatsapp_opt_in_source TEXT
        CHECK (
            whatsapp_opt_in_source IS NULL
            OR whatsapp_opt_in_source IN ('signup', 'profile_page', 'admin')
        ),
    whatsapp_phone_e164 TEXT,
    whatsapp_phone_verified_at TIMESTAMP WITH TIME ZONE,
    whatsapp_digest_time_local TEXT NOT NULL DEFAULT '08:00'
        CHECK (whatsapp_digest_time_local ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'),
    whatsapp_timezone TEXT NOT NULL DEFAULT 'UTC',
    whatsapp_opted_out_at TIMESTAMP WITH TIME ZONE,
    whatsapp_paused_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_preferences_opted_in
    ON notification_preferences(whatsapp_opted_in)
    WHERE whatsapp_opted_in = TRUE;
CREATE INDEX IF NOT EXISTS idx_notification_preferences_phone
    ON notification_preferences(whatsapp_phone_e164)
    WHERE whatsapp_phone_e164 IS NOT NULL;

CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    template_name TEXT NOT NULL,
    template_language TEXT NOT NULL DEFAULT 'en',
    phone_e164 TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    idempotency_key TEXT,
    provider_message_id TEXT,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'sent', 'delivered', 'read', 'failed', 'rate_limited', 'opt_out_blocked')),
    error_code TEXT,
    error_message TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_user_id ON whatsapp_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_status ON whatsapp_messages(status);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_phone_created ON whatsapp_messages(phone_e164, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_whatsapp_messages_idempotency_key
    ON whatsapp_messages(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS whatsapp_incoming_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_e164 TEXT NOT NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL
        CHECK (event_type IN ('text', 'status_update', 'button', 'interactive', 'other')),
    body TEXT,
    raw JSONB NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_incoming_events_phone
    ON whatsapp_incoming_events(phone_e164);
CREATE INDEX IF NOT EXISTS idx_whatsapp_incoming_events_user
    ON whatsapp_incoming_events(user_id)
    WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_whatsapp_incoming_events_received_at
    ON whatsapp_incoming_events(received_at DESC);

-- =====================================================
-- PART 10: SCRAPING JOBS TABLE
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
-- PART 11: ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE cvs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_incoming_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraping_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Users Table Policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.users;
CREATE POLICY "Users can view own profile"
    ON public.users FOR SELECT
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.users;
CREATE POLICY "Users can update own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

-- User Profiles Policies
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id);

-- CVs Policies
DROP POLICY IF EXISTS "Users can view own CVs" ON cvs;
CREATE POLICY "Users can view own CVs"
    ON cvs FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own CVs" ON cvs;
CREATE POLICY "Users can insert own CVs"
    ON cvs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own CVs" ON cvs;
CREATE POLICY "Users can update own CVs"
    ON cvs FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own CVs" ON cvs;
CREATE POLICY "Users can delete own CVs"
    ON cvs FOR DELETE
    USING (auth.uid() = user_id);

-- Job Matches Policies
DROP POLICY IF EXISTS "Users can view own job matches" ON job_matches;
CREATE POLICY "Users can view own job matches"
    ON job_matches FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own job matches" ON job_matches;
CREATE POLICY "Users can insert own job matches"
    ON job_matches FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own job matches" ON job_matches;
CREATE POLICY "Users can update own job matches"
    ON job_matches FOR UPDATE
    USING (auth.uid() = user_id);

-- Applications Policies
DROP POLICY IF EXISTS "Users can view own applications" ON applications;
CREATE POLICY "Users can view own applications"
    ON applications FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own applications" ON applications;
CREATE POLICY "Users can insert own applications"
    ON applications FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own applications" ON applications;
CREATE POLICY "Users can update own applications"
    ON applications FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own applications" ON applications;
CREATE POLICY "Users can delete own applications"
    ON applications FOR DELETE
    USING (auth.uid() = user_id);

-- Recommendations Policies
DROP POLICY IF EXISTS "Users can view own recommendations" ON job_recommendations;
CREATE POLICY "Users can view own recommendations"
    ON job_recommendations FOR SELECT
    USING (auth.uid() = user_id);

-- Embedding Policies
DROP POLICY IF EXISTS "Authenticated users can read job embeddings" ON job_embeddings;
CREATE POLICY "Authenticated users can read job embeddings"
    ON job_embeddings FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "Users can view own user embedding" ON user_embeddings;
CREATE POLICY "Users can view own user embedding"
    ON user_embeddings FOR SELECT
    USING (auth.uid() = user_id);

-- Notification / WhatsApp Policies
DROP POLICY IF EXISTS "Users can view own notification preferences" ON notification_preferences;
CREATE POLICY "Users can view own notification preferences"
    ON notification_preferences FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own notification preferences" ON notification_preferences;
CREATE POLICY "Users can insert own notification preferences"
    ON notification_preferences FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own notification preferences" ON notification_preferences;
CREATE POLICY "Users can update own notification preferences"
    ON notification_preferences FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view own WhatsApp messages" ON whatsapp_messages;
CREATE POLICY "Users can view own WhatsApp messages"
    ON whatsapp_messages FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view own WhatsApp incoming events" ON whatsapp_incoming_events;
CREATE POLICY "Users can view own WhatsApp incoming events"
    ON whatsapp_incoming_events FOR SELECT
    USING (auth.uid() = user_id);

-- Scraping Jobs Policies
DROP POLICY IF EXISTS "Users can view own scraping jobs" ON scraping_jobs;
CREATE POLICY "Users can view own scraping jobs"
    ON scraping_jobs FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own scraping jobs" ON scraping_jobs;
CREATE POLICY "Users can insert own scraping jobs"
    ON scraping_jobs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Jobs Policies (Public read for authenticated users)
DROP POLICY IF EXISTS "Authenticated users can view jobs" ON jobs;
CREATE POLICY "Authenticated users can view jobs"
    ON jobs FOR SELECT
    USING (auth.role() = 'authenticated');

-- =====================================================
-- PART 12: FUNCTIONS & TRIGGERS
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
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_cvs_updated_at ON cvs;
CREATE TRIGGER update_cvs_updated_at BEFORE UPDATE ON cvs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_job_matches_updated_at ON job_matches;
CREATE TRIGGER update_job_matches_updated_at BEFORE UPDATE ON job_matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_applications_updated_at ON applications;
CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_notification_preferences_updated_at ON notification_preferences;
CREATE TRIGGER update_notification_preferences_updated_at BEFORE UPDATE ON notification_preferences
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

DROP TRIGGER IF EXISTS ensure_single_active_cv_trigger ON cvs;
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
DROP TRIGGER IF EXISTS on_auth_user_created_sync ON auth.users;
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
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- =====================================================
-- PART 13: STORAGE POLICIES (for 'cvs' bucket)
-- =====================================================
-- Note: Create the 'cvs' storage bucket in Supabase Dashboard first
-- Then run these policies in SQL Editor

-- Policy: Users can upload their own CVs
-- Files are stored as: {user_id}/{cv_id}.{ext}
DROP POLICY IF EXISTS "Users can upload their own CVs" ON storage.objects;
CREATE POLICY "Users can upload their own CVs"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'cvs'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Policy: Users can read their own CVs
DROP POLICY IF EXISTS "Users can read their own CVs" ON storage.objects;
CREATE POLICY "Users can read their own CVs"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'cvs'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Policy: Users can update their own CVs
DROP POLICY IF EXISTS "Users can update their own CVs" ON storage.objects;
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
DROP POLICY IF EXISTS "Users can delete their own CVs" ON storage.objects;
CREATE POLICY "Users can delete their own CVs"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'cvs'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- =====================================================
-- PART 14: SYNC EXISTING DATA (Optional)
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
