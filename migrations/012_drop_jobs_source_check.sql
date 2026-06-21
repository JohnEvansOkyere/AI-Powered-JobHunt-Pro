-- Remove fixed-list validation from jobs.source.
--
-- Source names evolve as scrapers and ATS mirrors are added. A database CHECK
-- constraint caused ATS recruiter jobs to fail until migration 011 added the
-- new value. Keep source validation in application code instead of requiring a
-- schema migration for every new source.

ALTER TABLE jobs
  DROP CONSTRAINT IF EXISTS jobs_source_check;
