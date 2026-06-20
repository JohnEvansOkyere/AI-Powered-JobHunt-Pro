-- Migration 006: Reserved no-op
--
-- This file intentionally fills the historical numbering gap between
-- 005_add_external_jobs_support.sql and 007_remove_cv_tailoring.sql.
-- It makes fresh-environment migration ordering explicit without changing
-- any database schema.

BEGIN;

COMMIT;
