-- Migration 019: private, editable tailored CV drafts with revision history.
-- Rollback: DROP TABLE cv_generation_revisions; DROP TABLE cv_generations;

BEGIN;

CREATE TABLE IF NOT EXISTS cv_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    source_cv_id UUID NOT NULL REFERENCES cvs(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    content JSONB NOT NULL,
    ai_content JSONB NOT NULL,
    source_content_hash TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    ai_provider TEXT,
    prompt_version TEXT NOT NULL DEFAULT 'cv-tailor-v1',
    validation_warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cv_generations_user_id ON cv_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_cv_generations_source_cv_id ON cv_generations(source_cv_id);
CREATE INDEX IF NOT EXISTS idx_cv_generations_job_id ON cv_generations(job_id);
CREATE INDEX IF NOT EXISTS idx_cv_generations_user_updated
    ON cv_generations(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS cv_generation_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id UUID NOT NULL REFERENCES cv_generations(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    content JSONB NOT NULL,
    change_source TEXT NOT NULL CHECK (change_source IN ('ai', 'user', 'reset', 'restore')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_cv_generation_revision UNIQUE (generation_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_cv_generation_revisions_generation_id
    ON cv_generation_revisions(generation_id);

ALTER TABLE cv_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv_generation_revisions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own CV generations" ON cv_generations;
CREATE POLICY "Users can view own CV generations" ON cv_generations FOR SELECT
    USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "Users can insert own CV generations" ON cv_generations;
CREATE POLICY "Users can insert own CV generations" ON cv_generations FOR INSERT
    WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "Users can update own CV generations" ON cv_generations;
CREATE POLICY "Users can update own CV generations" ON cv_generations FOR UPDATE
    USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "Users can delete own CV generations" ON cv_generations;
CREATE POLICY "Users can delete own CV generations" ON cv_generations FOR DELETE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view own CV generation revisions" ON cv_generation_revisions;
CREATE POLICY "Users can view own CV generation revisions" ON cv_generation_revisions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM cv_generations generation
        WHERE generation.id = generation_id AND generation.user_id = auth.uid()
    ));
DROP POLICY IF EXISTS "Users can insert own CV generation revisions" ON cv_generation_revisions;
CREATE POLICY "Users can insert own CV generation revisions" ON cv_generation_revisions FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM cv_generations generation
        WHERE generation.id = generation_id AND generation.user_id = auth.uid()
    ));

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_cv_generations_updated_at ON cv_generations;
CREATE TRIGGER update_cv_generations_updated_at
    BEFORE UPDATE ON cv_generations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;
