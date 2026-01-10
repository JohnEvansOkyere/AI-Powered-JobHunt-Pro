-- Migration: Add Saved Jobs Feature
-- Date: 2026-01-10
-- Description: Adds status tracking, saved_at, and expires_at columns to applications table

-- Step 1: Drop old constraint
ALTER TABLE applications
DROP CONSTRAINT IF EXISTS applications_status_check;

-- Step 2: Add new columns
ALTER TABLE applications
ADD COLUMN IF NOT EXISTS saved_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;

-- Step 3: Add new constraint with expanded status values
ALTER TABLE applications
ADD CONSTRAINT applications_status_check
CHECK (status IN ('saved', 'draft', 'reviewed', 'finalized', 'sent', 'submitted', 'interviewing', 'rejected', 'offer'));

-- Step 4: Update default status to 'saved'
ALTER TABLE applications
ALTER COLUMN status SET DEFAULT 'saved';

-- Step 5: Create index on expires_at for cleanup queries
CREATE INDEX IF NOT EXISTS idx_applications_expires_at ON applications(expires_at) WHERE expires_at IS NOT NULL;

-- Step 6: Create index on saved_at
CREATE INDEX IF NOT EXISTS idx_applications_saved_at ON applications(saved_at) WHERE saved_at IS NOT NULL;

-- Step 7: Update existing records (set draft status records to have saved_at)
UPDATE applications
SET saved_at = created_at
WHERE saved_at IS NULL AND created_at IS NOT NULL;

COMMENT ON COLUMN applications.saved_at IS 'Timestamp when user clicked Save Job button';
COMMENT ON COLUMN applications.expires_at IS 'Expiry date for saved jobs (saved_at + 10 days). NULL means no expiry.';
COMMENT ON COLUMN applications.status IS 'Application status: saved (bookmarked), draft (CV generated), reviewed, finalized, sent, submitted, interviewing, rejected, offer';
