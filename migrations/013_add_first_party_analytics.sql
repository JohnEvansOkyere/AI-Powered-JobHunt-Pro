BEGIN;

-- First-party analytics for anonymous and authenticated product usage.
-- No IP address or raw form contents are stored. The backend writes these
-- tables after validating the event payload and optional Supabase identity.
CREATE TABLE IF NOT EXISTS analytics_sessions (
    id UUID PRIMARY KEY,
    anonymous_id VARCHAR(80) NOT NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    landing_path TEXT,
    last_path TEXT,
    referrer TEXT,
    user_agent TEXT,
    page_views INTEGER NOT NULL DEFAULT 0,
    event_count INTEGER NOT NULL DEFAULT 0,
    engaged_seconds INTEGER NOT NULL DEFAULT 0,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_analytics_sessions_anonymous_first_seen
    ON analytics_sessions(anonymous_id, first_seen_at);
CREATE INDEX IF NOT EXISTS idx_analytics_sessions_user_last_seen
    ON analytics_sessions(user_id, last_seen_at);

CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    anonymous_id VARCHAR(80) NOT NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    event_name VARCHAR(60) NOT NULL,
    path TEXT NOT NULL,
    referrer TEXT,
    target TEXT,
    label TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    duration_ms INTEGER,
    user_agent TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON analytics_events(session_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_anonymous_id ON analytics_events(anonymous_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_name_occurred ON analytics_events(event_name, occurred_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_path_occurred ON analytics_events(path, occurred_at);

ALTER TABLE analytics_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;

COMMIT;

-- Rollback:
-- DROP TABLE IF EXISTS analytics_events;
-- DROP TABLE IF EXISTS analytics_sessions;
