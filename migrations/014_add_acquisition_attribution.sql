BEGIN;

ALTER TABLE analytics_sessions
    ADD COLUMN IF NOT EXISTS acquisition_source VARCHAR(80),
    ADD COLUMN IF NOT EXISTS acquisition_medium VARCHAR(80),
    ADD COLUMN IF NOT EXISTS acquisition_campaign VARCHAR(160),
    ADD COLUMN IF NOT EXISTS acquisition_content VARCHAR(160),
    ADD COLUMN IF NOT EXISTS acquisition_term VARCHAR(160);

CREATE INDEX IF NOT EXISTS idx_analytics_sessions_acquisition
    ON analytics_sessions(acquisition_source, acquisition_medium, first_seen_at);

COMMIT;

-- Rollback:
-- DROP INDEX IF EXISTS idx_analytics_sessions_acquisition;
-- ALTER TABLE analytics_sessions
--     DROP COLUMN IF EXISTS acquisition_term,
--     DROP COLUMN IF EXISTS acquisition_content,
--     DROP COLUMN IF EXISTS acquisition_campaign,
--     DROP COLUMN IF EXISTS acquisition_medium,
--     DROP COLUMN IF EXISTS acquisition_source;
