-- Migration 006: Loyalty Score System
-- Creates tables for tracking loyalty scores, moderation events, and score history

-- Moderation events table - tracks all events that affect loyalty scores
CREATE TABLE moderation_events (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    content_pk UUID NOT NULL,
    outcome VARCHAR(20) NOT NULL,
    score_delta INTEGER NOT NULL DEFAULT 0,
    moderator_pk UUID REFERENCES users(pk) ON DELETE SET NULL,
    reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Indexes for common queries
    INDEX idx_moderation_events_user_pk (user_pk),
    INDEX idx_moderation_events_created_at (created_at DESC),
    INDEX idx_moderation_events_event_type (event_type),
    INDEX idx_moderation_events_content (content_type, content_pk),
    INDEX idx_moderation_events_moderator (moderator_pk)
);

-- Loyalty score history - tracks score changes over time
CREATE TABLE loyalty_score_history (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    old_score INTEGER NOT NULL,
    new_score INTEGER NOT NULL,
    score_delta INTEGER NOT NULL,
    event_pk UUID REFERENCES moderation_events(pk) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Indexes for queries
    INDEX idx_loyalty_score_history_user_pk (user_pk),
    INDEX idx_loyalty_score_history_created_at (created_at DESC),
    INDEX idx_loyalty_score_history_event_pk (event_pk)
);

-- Manual loyalty score adjustments - admin overrides
CREATE TABLE loyalty_score_adjustments (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    admin_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    old_score INTEGER NOT NULL,
    new_score INTEGER NOT NULL,
    score_delta INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Indexes
    INDEX idx_loyalty_score_adjustments_user_pk (user_pk),
    INDEX idx_loyalty_score_adjustments_admin_pk (admin_pk),
    INDEX idx_loyalty_score_adjustments_created_at (created_at DESC)
);

-- Add loyalty score breakdown cache table for performance
CREATE TABLE loyalty_score_breakdown_cache (
    user_pk UUID PRIMARY KEY REFERENCES users(pk) ON DELETE CASCADE,
    post_score INTEGER NOT NULL DEFAULT 0,
    topic_score INTEGER NOT NULL DEFAULT 0,
    comment_score INTEGER NOT NULL DEFAULT 0,
    appeal_score INTEGER NOT NULL DEFAULT 0,
    manual_adjustment_score INTEGER NOT NULL DEFAULT 0,
    total_score INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Ensure total matches sum of components
    CONSTRAINT loyalty_breakdown_total_check
        CHECK (total_score = post_score + topic_score + comment_score + appeal_score + manual_adjustment_score)
);

-- Trigger to update user loyalty_score when breakdown changes
CREATE OR REPLACE FUNCTION update_user_loyalty_score()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users
    SET loyalty_score = NEW.total_score,
        updated_at = NOW()
    WHERE pk = NEW.user_pk;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_loyalty_score
    AFTER INSERT OR UPDATE ON loyalty_score_breakdown_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_user_loyalty_score();

-- Initialize breakdown cache for existing users
INSERT INTO loyalty_score_breakdown_cache (user_pk, total_score)
SELECT pk, COALESCE(loyalty_score, 0)
FROM users
ON CONFLICT (user_pk) DO NOTHING;

-- Add constraints for valid enum values
ALTER TABLE moderation_events ADD CONSTRAINT moderation_events_event_type_check
    CHECK (event_type IN (
        'post_moderation', 'topic_moderation', 'comment_moderation',
        'appeal_submitted', 'appeal_approved', 'appeal_denied'
    ));

ALTER TABLE moderation_events ADD CONSTRAINT moderation_events_content_type_check
    CHECK (content_type IN ('post', 'topic', 'comment', 'appeal'));

ALTER TABLE moderation_events ADD CONSTRAINT moderation_events_outcome_check
    CHECK (outcome IN ('approved', 'rejected', 'flagged', 'removed', 'warning', 'suspended'));

-- Comments for documentation
COMMENT ON TABLE moderation_events IS 'Records all moderation events that affect user loyalty scores';
COMMENT ON TABLE loyalty_score_history IS 'Tracks historical changes to user loyalty scores';
COMMENT ON TABLE loyalty_score_adjustments IS 'Manual loyalty score adjustments made by administrators';
COMMENT ON TABLE loyalty_score_breakdown_cache IS 'Cached breakdown of loyalty scores by content type for performance';
