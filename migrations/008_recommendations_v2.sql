-- Migration 008: Recommendations V2 schema
-- Part of docs/RECOMMENDATIONS_V2_PLAN.md §5.1.
--
-- What this does:
--   1. Enables pgvector (idempotent).
--   2. Creates `job_embeddings` and `user_embeddings` (cached vectors, model-tagged).
--   3. Extends `job_recommendations` with tiering + sub-score columns + user_id FK.
--
-- Dimension note:
--   Vectors are sized for Gemini `text-embedding-004` (768 dims). If you flip
--   AI_EMBEDDING_PROVIDER=openai you MUST re-embed; see §3.1 of the plan. Rows
--   produced by a different model stay in-place but are ignored at read time
--   because queries join on `model`.
--
-- Safety:
--   - All CREATE / ALTER statements are idempotent via IF [NOT] EXISTS.
--   - Column additions on `job_recommendations` keep existing rows. New
--     columns default to sensible values (`tier='tier2'`, sub-scores NULL).
--   - pgvector's `vector` type degrades gracefully: if the extension is not
--     available on your Postgres, run the `float8[]` fallback block at the
--     bottom of this file instead.
--
-- Rollback (manual):
--   DROP TABLE job_embeddings, user_embeddings;
--   ALTER TABLE job_recommendations
--     DROP COLUMN tier,
--     DROP COLUMN semantic_fit,
--     DROP COLUMN title_alignment,
--     DROP COLUMN skill_overlap,
--     DROP COLUMN freshness,
--     DROP COLUMN channel_bonus,
--     DROP COLUMN interest_affinity,
--     DROP COLUMN llm_rerank_score,
--     DROP CONSTRAINT fk_job_recommendations_user_id;

BEGIN;

-- 1. pgvector. Supabase Postgres ships with it; this is a no-op on most managed DBs.
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Cached job embeddings.
CREATE TABLE IF NOT EXISTS job_embeddings (
    job_id       UUID        PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    embedding    vector(768) NOT NULL,
    model        TEXT        NOT NULL DEFAULT 'text-embedding-004',
    source_hash  TEXT        NOT NULL,
    embedded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  job_embeddings             IS 'Cached job embeddings. Queries MUST filter by `model` (see RECOMMENDATIONS_V2_PLAN §3.1).';
COMMENT ON COLUMN job_embeddings.embedding   IS 'Vector. Dim = 768 for Gemini text-embedding-004.';
COMMENT ON COLUMN job_embeddings.model       IS 'Producing model, source of truth for vector dimensionality/provider.';
COMMENT ON COLUMN job_embeddings.source_hash IS 'Stable hash of the text we embedded; short-circuits re-embedding when unchanged.';

-- HNSW ANN index for fast top-K cosine search. Only add when embedding fits
-- the index's dim limit (pgvector supports up to 2000 for HNSW).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_job_embeddings_hnsw'
    ) THEN
        EXECUTE 'CREATE INDEX idx_job_embeddings_hnsw '
             || 'ON job_embeddings USING hnsw (embedding vector_cosine_ops)';
    END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_job_embeddings_model
    ON job_embeddings(model);

-- 3. Cached user embeddings (profile + CV distilled text).
CREATE TABLE IF NOT EXISTS user_embeddings (
    user_id      UUID        PRIMARY KEY,
    embedding    vector(768) NOT NULL,
    model        TEXT        NOT NULL DEFAULT 'text-embedding-004',
    source_hash  TEXT        NOT NULL,
    embedded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  user_embeddings           IS 'Cached user-intent embeddings. Refreshed on profile/CV change.';
COMMENT ON COLUMN user_embeddings.model     IS 'Must match job_embeddings.model at match time.';

CREATE INDEX IF NOT EXISTS idx_user_embeddings_model
    ON user_embeddings(model);

-- 4. Extend job_recommendations with tiering + sub-scores.
ALTER TABLE job_recommendations
    ADD COLUMN IF NOT EXISTS tier               TEXT             NOT NULL DEFAULT 'tier2',
    ADD COLUMN IF NOT EXISTS semantic_fit       DOUBLE PRECISION NULL,
    ADD COLUMN IF NOT EXISTS title_alignment    DOUBLE PRECISION NULL,
    ADD COLUMN IF NOT EXISTS skill_overlap      DOUBLE PRECISION NULL,
    ADD COLUMN IF NOT EXISTS freshness          DOUBLE PRECISION NULL,
    ADD COLUMN IF NOT EXISTS channel_bonus      DOUBLE PRECISION NULL,
    ADD COLUMN IF NOT EXISTS interest_affinity  DOUBLE PRECISION NULL,
    ADD COLUMN IF NOT EXISTS llm_rerank_score   DOUBLE PRECISION NULL;

-- CHECK for tier values. Drop+recreate so re-running the migration is safe.
ALTER TABLE job_recommendations DROP CONSTRAINT IF EXISTS job_recommendations_tier_check;
ALTER TABLE job_recommendations
    ADD CONSTRAINT job_recommendations_tier_check
    CHECK (tier IN ('tier1', 'tier2', 'tier3'));

COMMENT ON COLUMN job_recommendations.tier              IS 'Recommendation tier: tier1=Highly Recommended, tier2=Likely a Fit, tier3=All Roles.';
COMMENT ON COLUMN job_recommendations.semantic_fit      IS 'Cosine similarity between user and job embeddings, 0..1.';
COMMENT ON COLUMN job_recommendations.title_alignment   IS 'Title overlap score against user target titles, 0..1.';
COMMENT ON COLUMN job_recommendations.skill_overlap     IS 'Fraction of user top-15 skills found in job text, 0..1.';
COMMENT ON COLUMN job_recommendations.freshness         IS 'Age-based decay on posted_date, 0..1.';
COMMENT ON COLUMN job_recommendations.channel_bonus     IS 'Source quality bonus (recruiter > scraped > external), 0..1.';
COMMENT ON COLUMN job_recommendations.interest_affinity IS 'Cosine to the centroid of the user\'s recent saved/applied jobs, 0..1 or NULL.';
COMMENT ON COLUMN job_recommendations.llm_rerank_score  IS 'Reranker score (0..100). NULL if this row was not reranked.';

-- Re-read indexes for the new access pattern: "give me Tier 1 for user X".
CREATE INDEX IF NOT EXISTS idx_recommendations_user_tier_score
    ON job_recommendations(user_id, tier, match_score DESC);

-- 5. Add the missing user_id FK the audit flagged (P2.12). Do this last, after
--    any orphaned rows have been cleaned up during the Phase 1 backfill.
--    We use NOT VALID + VALIDATE so we don't block on a full-table scan
--    under lock on a live DB.
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
                REFERENCES users(id)
                ON DELETE CASCADE
                NOT VALID;

            -- Validate outside the DDL lock window.
            ALTER TABLE job_recommendations
                VALIDATE CONSTRAINT fk_job_recommendations_user_id;
        EXCEPTION WHEN others THEN
            -- If `users` table name differs in this environment, surface a
            -- clear message instead of aborting the whole migration silently.
            RAISE NOTICE 'Could not add fk_job_recommendations_user_id: %', SQLERRM;
        END;
    END IF;
END$$;

COMMIT;

-- ---------------------------------------------------------------------------
-- Fallback: pgvector not available.
-- Run the block below INSTEAD of the `vector(768)` columns above if your
-- Postgres does not ship with pgvector. Read-path performance is worse
-- because ANN is unavailable; the Python pipeline will fall back to an
-- in-memory cosine sort over ≤ a few thousand rows.
--
-- CREATE TABLE IF NOT EXISTS job_embeddings (
--     job_id       UUID        PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
--     embedding    DOUBLE PRECISION[] NOT NULL,
--     model        TEXT        NOT NULL DEFAULT 'text-embedding-004',
--     source_hash  TEXT        NOT NULL,
--     embedded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
-- );
-- CREATE TABLE IF NOT EXISTS user_embeddings (
--     user_id      UUID        PRIMARY KEY,
--     embedding    DOUBLE PRECISION[] NOT NULL,
--     model        TEXT        NOT NULL DEFAULT 'text-embedding-004',
--     source_hash  TEXT        NOT NULL,
--     embedded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
-- );
