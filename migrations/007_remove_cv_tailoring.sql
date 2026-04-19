-- Migration 007: Remove CV tailoring feature
-- Part of the V2 pivot (docs/RECOMMENDATIONS_V2_PLAN.md §4).
-- Drops generation-specific columns from `applications` and tightens the status enum.
--
-- Safe to run on a live database:
--   - ALTER TABLE ... DROP COLUMN IF EXISTS is idempotent.
--   - The status backfill only touches rows outside the new enum.
--   - CHECK constraint is dropped then re-added.
--
-- Rollback (manual): re-add the dropped columns as nullable. Historical
-- tailored-CV files must be re-uploaded; they are deleted from Storage
-- by `backend/scripts/maintenance/delete_tailored_cvs.py`.

BEGIN;

-- 1. Drop CV tailoring columns.
ALTER TABLE applications DROP COLUMN IF EXISTS tailored_cv_path;
ALTER TABLE applications DROP COLUMN IF EXISTS cover_letter;
ALTER TABLE applications DROP COLUMN IF EXISTS application_email;
ALTER TABLE applications DROP COLUMN IF EXISTS ai_model_used;
ALTER TABLE applications DROP COLUMN IF EXISTS generation_prompt;
ALTER TABLE applications DROP COLUMN IF EXISTS generation_settings;
ALTER TABLE applications DROP COLUMN IF EXISTS user_edits;

-- 2. Backfill deprecated status values to 'saved' before tightening the enum.
--    New enum: saved | applied | dismissed | hidden | interviewing | rejected | offer
UPDATE applications
SET status = 'saved'
WHERE status IN ('draft', 'reviewed', 'finalized', 'sent');

UPDATE applications
SET status = 'applied'
WHERE status = 'submitted';

-- 3. Swap the CHECK constraint.
ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_status_check;
ALTER TABLE applications
  ADD CONSTRAINT applications_status_check
  CHECK (status IN ('saved', 'applied', 'dismissed', 'hidden', 'interviewing', 'rejected', 'offer'));

-- 4. Default value aligned with new enum.
ALTER TABLE applications ALTER COLUMN status SET DEFAULT 'saved';

COMMIT;
