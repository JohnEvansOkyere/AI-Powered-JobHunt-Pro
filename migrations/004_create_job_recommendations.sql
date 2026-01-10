-- Migration: Create Job Recommendations Table
-- Date: 2026-01-10
-- Description: Pre-computed job recommendations to avoid real-time AI matching delays

-- Step 1: Create job_recommendations table
CREATE TABLE IF NOT EXISTS job_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    match_score FLOAT NOT NULL,
    match_reason TEXT,  -- Why this job was recommended (for explainability)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,  -- created_at + 3 days

    -- Prevent duplicate recommendations
    CONSTRAINT unique_user_job_recommendation UNIQUE(user_id, job_id)
);

-- Step 2: Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_recommendations_user_expires
ON job_recommendations(user_id, expires_at DESC)
WHERE expires_at > NOW();

CREATE INDEX IF NOT EXISTS idx_recommendations_score
ON job_recommendations(user_id, match_score DESC);

CREATE INDEX IF NOT EXISTS idx_recommendations_expires
ON job_recommendations(expires_at);

-- Step 3: Add RLS (Row Level Security) policies
ALTER TABLE job_recommendations ENABLE ROW LEVEL SECURITY;

-- Users can only see their own recommendations
CREATE POLICY "Users can view own recommendations"
ON job_recommendations
FOR SELECT
USING (user_id = auth.uid());

-- Step 4: Add comments
COMMENT ON TABLE job_recommendations IS 'Pre-computed job recommendations to avoid real-time AI matching delays';
COMMENT ON COLUMN job_recommendations.user_id IS 'User who receives this recommendation';
COMMENT ON COLUMN job_recommendations.job_id IS 'Recommended job';
COMMENT ON COLUMN job_recommendations.match_score IS 'AI-computed match score (0.0 to 1.0)';
COMMENT ON COLUMN job_recommendations.match_reason IS 'Brief explanation of why this job matches (for transparency)';
COMMENT ON COLUMN job_recommendations.expires_at IS 'Recommendations expire after 3 days and are regenerated';
