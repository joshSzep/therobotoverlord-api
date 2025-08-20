-- Migration: 004_leaderboard_system.sql
-- Description: Create leaderboard system with materialized views and ranking tables
-- Author: System
-- Date: 2025-08-19

-- step: create_leaderboard_materialized_view
-- Materialized view for efficient leaderboard queries with pre-calculated ranks
CREATE MATERIALIZED VIEW leaderboard_rankings AS
SELECT
    u.pk as user_pk,
    u.username,
    u.loyalty_score,
    u.created_at as user_created_at,
    u.updated_at as user_updated_at,
    ROW_NUMBER() OVER (ORDER BY u.loyalty_score DESC, u.created_at ASC) as rank,
    -- Percentile calculation for topic creation privilege (0.0 = top, 1.0 = bottom)
    PERCENT_RANK() OVER (ORDER BY u.loyalty_score DESC) as percentile_rank,
    -- Count of topics created by this user
    COALESCE(topic_counts.topic_count, 0) as topics_created_count,
    -- Topic creation privilege (top 10%)
    CASE
        WHEN PERCENT_RANK() OVER (ORDER BY u.loyalty_score DESC) <= 0.1 THEN true
        ELSE false
    END as topic_creation_enabled,
    NOW() as calculated_at
FROM users u
LEFT JOIN (
    SELECT
        author_pk,
        COUNT(*) as topic_count
    FROM topics
    WHERE status = 'approved'
    GROUP BY author_pk
) topic_counts ON u.pk = topic_counts.author_pk
WHERE u.is_banned = FALSE
ORDER BY u.loyalty_score DESC, u.created_at ASC;

-- step: create_leaderboard_indexes
-- Indexes for fast leaderboard queries
CREATE UNIQUE INDEX idx_leaderboard_rank ON leaderboard_rankings(rank);
CREATE UNIQUE INDEX idx_leaderboard_user ON leaderboard_rankings(user_pk);
CREATE INDEX idx_leaderboard_score ON leaderboard_rankings(loyalty_score DESC);
CREATE INDEX idx_leaderboard_percentile ON leaderboard_rankings(percentile_rank);
CREATE INDEX idx_leaderboard_username ON leaderboard_rankings USING gin(username gin_trgm_ops);

-- step: create_leaderboard_snapshots_table
-- Historical leaderboard data for tracking rank changes over time
CREATE TABLE leaderboard_snapshots (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    username VARCHAR(100) NOT NULL, -- Snapshot of username at time
    rank INTEGER NOT NULL,
    loyalty_score INTEGER NOT NULL,
    percentile_rank DECIMAL(10,8) NOT NULL,
    topics_created_count INTEGER DEFAULT 0,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_pk, snapshot_date)
);

-- step: create_leaderboard_snapshots_indexes
-- Indexes for historical leaderboard queries
CREATE INDEX idx_snapshots_user_date ON leaderboard_snapshots(user_pk, snapshot_date DESC);
CREATE INDEX idx_snapshots_date ON leaderboard_snapshots(snapshot_date DESC);
CREATE INDEX idx_snapshots_rank ON leaderboard_snapshots(snapshot_date DESC, rank);

-- step: create_leaderboard_cache_table
-- Cache table for expensive leaderboard queries
CREATE TABLE leaderboard_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    cache_data JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- step: create_leaderboard_cache_indexes
CREATE INDEX idx_leaderboard_cache_expires ON leaderboard_cache(expires_at);

-- step: create_leaderboard_refresh_function
-- Function to refresh the materialized view and update cache
CREATE OR REPLACE FUNCTION refresh_leaderboard_rankings()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    -- Refresh the materialized view concurrently to avoid blocking
    REFRESH MATERIALIZED VIEW CONCURRENTLY leaderboard_rankings;

    -- Clear expired cache entries
    DELETE FROM leaderboard_cache WHERE expires_at < NOW();

    -- Log the refresh
    INSERT INTO system_logs (event_type, message, created_at)
    VALUES ('leaderboard_refresh', 'Leaderboard rankings refreshed', NOW())
    ON CONFLICT DO NOTHING;

EXCEPTION
    WHEN OTHERS THEN
        -- Log error but don't fail the transaction
        INSERT INTO system_logs (event_type, message, error_details, created_at)
        VALUES (
            'leaderboard_refresh_error',
            'Failed to refresh leaderboard rankings',
            SQLERRM,
            NOW()
        );
END;
$$;

-- step: create_daily_snapshot_function
-- Function to create daily leaderboard snapshots
CREATE OR REPLACE FUNCTION create_daily_leaderboard_snapshot()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insert today's snapshot from current rankings
    INSERT INTO leaderboard_snapshots (
        user_pk,
        username,
        rank,
        loyalty_score,
        percentile_rank,
        topics_created_count,
        snapshot_date
    )
    SELECT
        user_pk,
        username,
        rank,
        loyalty_score,
        percentile_rank,
        topics_created_count,
        CURRENT_DATE
    FROM leaderboard_rankings
    ON CONFLICT (user_pk, snapshot_date)
    DO UPDATE SET
        username = EXCLUDED.username,
        rank = EXCLUDED.rank,
        loyalty_score = EXCLUDED.loyalty_score,
        percentile_rank = EXCLUDED.percentile_rank,
        topics_created_count = EXCLUDED.topics_created_count;

    -- Clean up old snapshots (keep 90 days)
    DELETE FROM leaderboard_snapshots
    WHERE snapshot_date < CURRENT_DATE - INTERVAL '90 days';

END;
$$;

-- step: enable_trigram_extension
-- Enable pg_trgm extension for username search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- step: create_system_logs_table_if_not_exists
-- Create system logs table if it doesn't exist (for leaderboard refresh logging)
CREATE TABLE IF NOT EXISTS system_logs (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    error_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_logs_event_type ON system_logs(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at DESC);
