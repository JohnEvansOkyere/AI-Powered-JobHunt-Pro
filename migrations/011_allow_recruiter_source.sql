-- 011_allow_recruiter_source.sql
-- Fix: ATS-mirrored jobs use source = 'recruiter', but the jobs_source_check
-- constraint (from 005) never included it, so the ATS sync failed with
-- CheckViolation on insert. Migration 010 added the origin_* columns for ATS
-- mirroring but missed widening this constraint.
--
-- Recreate the constraint with the full current set of source values written by
-- the app (all active scrapers + ATS 'recruiter' + legacy values).
--
-- Safe to run more than once. If ADD CONSTRAINT fails, run
--   SELECT DISTINCT source FROM jobs;
-- first and add any missing value to the list below.

ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_source_check;

ALTER TABLE jobs ADD CONSTRAINT jobs_source_check
CHECK (source IN (
    -- active scrapers
    'adzuna', 'ai', 'arbeitnow', 'findwork', 'hiringcafe', 'indeed',
    'joinrise', 'jooble', 'linkedin', 'remoteok', 'remotive', 'serpapi',
    -- legacy (kept for existing rows)
    'glassdoor', 'external',
    -- ATS-mirrored recruiter jobs
    'recruiter'
));

-- Rollback:
-- ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_source_check;
-- ALTER TABLE jobs ADD CONSTRAINT jobs_source_check
-- CHECK (source IN ('indeed','linkedin','glassdoor','arbeitnow','remoteok','serpapi','external'));
