-- Migration: Add External Jobs Support
-- Date: 2026-01-24
-- Description: Add columns to support user-submitted external job postings

-- Step 1: Add new columns to jobs table
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS source_url TEXT,
ADD COLUMN IF NOT EXISTS added_by_user_id UUID,
ADD COLUMN IF NOT EXISTS salary_min TEXT,
ADD COLUMN IF NOT EXISTS salary_max TEXT,
ADD COLUMN IF NOT EXISTS salary_currency VARCHAR(10),
ADD COLUMN IF NOT EXISTS remote_option VARCHAR(10),
ADD COLUMN IF NOT EXISTS experience_level VARCHAR(20),
ADD COLUMN IF NOT EXISTS requirements TEXT,
ADD COLUMN IF NOT EXISTS responsibilities TEXT,
ADD COLUMN IF NOT EXISTS skills TEXT;

-- Step 2: Modify existing columns to support external jobs
-- Make job_link nullable (external jobs might not have a direct link)
ALTER TABLE jobs ALTER COLUMN job_link DROP NOT NULL;

-- Make source_id nullable (external jobs won't have scraped IDs)
ALTER TABLE jobs ALTER COLUMN source_id DROP NOT NULL;

-- Step 3: Update the source column check constraint to include 'external'
-- First, drop the existing constraint if it exists
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_source_check;

-- Add new constraint including 'external' source and existing scraped sources
ALTER TABLE jobs ADD CONSTRAINT jobs_source_check 
CHECK (source IN ('indeed', 'linkedin', 'glassdoor', 'arbeitnow', 'remoteok', 'serpapi', 'external'));

-- Step 4: Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_jobs_added_by_user_id ON jobs(added_by_user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_source_url ON jobs(source_url);
CREATE INDEX IF NOT EXISTS idx_jobs_experience_level ON jobs(experience_level);

-- Step 5: Add comments for documentation
COMMENT ON COLUMN jobs.source_url IS 'Original URL where the job was found (for reference)';
COMMENT ON COLUMN jobs.added_by_user_id IS 'User who manually added this external job posting';
COMMENT ON COLUMN jobs.salary_min IS 'Minimum salary amount (text to handle various formats)';
COMMENT ON COLUMN jobs.salary_max IS 'Maximum salary amount (text to handle various formats)';
COMMENT ON COLUMN jobs.salary_currency IS 'Currency code for salary (e.g., USD, EUR, GBP)';
COMMENT ON COLUMN jobs.remote_option IS 'Remote work availability (yes/no/hybrid)';
COMMENT ON COLUMN jobs.experience_level IS 'Required experience level (entry/mid/senior/executive)';
COMMENT ON COLUMN jobs.requirements IS 'JSON array of job requirements as text';
COMMENT ON COLUMN jobs.responsibilities IS 'JSON array of job responsibilities as text';
COMMENT ON COLUMN jobs.skills IS 'JSON array of required skills as text';
