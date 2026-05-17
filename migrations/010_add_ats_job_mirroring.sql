BEGIN;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS origin_system TEXT,
    ADD COLUMN IF NOT EXISTS origin_job_id TEXT,
    ADD COLUMN IF NOT EXISTS origin_updated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS ats_organization_id UUID,
    ADD COLUMN IF NOT EXISTS organization_name TEXT,
    ADD COLUMN IF NOT EXISTS organization_logo_url TEXT,
    ADD COLUMN IF NOT EXISTS publication_status TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_origin_system_job_id
    ON jobs(origin_system, origin_job_id)
    WHERE origin_system IS NOT NULL AND origin_job_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_origin_system ON jobs(origin_system);
CREATE INDEX IF NOT EXISTS idx_jobs_origin_updated_at ON jobs(origin_updated_at);
CREATE INDEX IF NOT EXISTS idx_jobs_ats_organization_id ON jobs(ats_organization_id);
CREATE INDEX IF NOT EXISTS idx_jobs_publication_status ON jobs(publication_status);

COMMIT;

-- Rollback:
-- DROP INDEX IF EXISTS idx_jobs_publication_status;
-- DROP INDEX IF EXISTS idx_jobs_ats_organization_id;
-- DROP INDEX IF EXISTS idx_jobs_origin_updated_at;
-- DROP INDEX IF EXISTS idx_jobs_origin_system;
-- DROP INDEX IF EXISTS uq_jobs_origin_system_job_id;
-- ALTER TABLE jobs DROP COLUMN IF EXISTS publication_status,
--                  DROP COLUMN IF EXISTS organization_logo_url,
--                  DROP COLUMN IF EXISTS organization_name,
--                  DROP COLUMN IF EXISTS ats_organization_id,
--                  DROP COLUMN IF EXISTS origin_updated_at,
--                  DROP COLUMN IF EXISTS origin_job_id,
--                  DROP COLUMN IF EXISTS origin_system;
