BEGIN;

-- Jobs imported from the weekly ALX Ghana Community digest carry a closing
-- date. Store it so expired listings can be hidden from the job board.
ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS application_deadline TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_jobs_application_deadline
    ON public.jobs(application_deadline)
    WHERE application_deadline IS NOT NULL;

-- The "Local Jobs" board now serves recruiter (ATS) and ALX jobs together.
CREATE INDEX IF NOT EXISTS idx_jobs_source_posted_date
    ON public.jobs(source, posted_date DESC);

COMMIT;

-- Rollback:
-- DROP INDEX IF EXISTS idx_jobs_source_posted_date;
-- DROP INDEX IF EXISTS idx_jobs_application_deadline;
-- ALTER TABLE public.jobs DROP COLUMN IF EXISTS application_deadline;
