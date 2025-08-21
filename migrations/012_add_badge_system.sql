-- Migration: Add Badge System
-- Description: Create badges and user_badges tables for gamification system

-- Badges table for badge definitions
CREATE TABLE badges (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    badge_type VARCHAR(20) NOT NULL CHECK (badge_type IN ('positive', 'negative')),
    criteria_config JSONB NOT NULL, -- Flexible criteria storage
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User badges junction table
CREATE TABLE user_badges (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    badge_pk UUID NOT NULL REFERENCES badges(pk) ON DELETE CASCADE,
    awarded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    awarded_for_post_pk UUID REFERENCES posts(pk),
    awarded_for_topic_pk UUID REFERENCES topics(pk),
    awarded_by_event VARCHAR(50), -- 'moderation_outcome', 'manual_award', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_pk, badge_pk) -- One badge per user
);

-- Indexes for performance
CREATE INDEX idx_badges_type ON badges(badge_type);
CREATE INDEX idx_badges_active ON badges(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_badges_name ON badges(name);

CREATE INDEX idx_user_badges_user ON user_badges(user_pk);
CREATE INDEX idx_user_badges_badge ON user_badges(badge_pk);
CREATE INDEX idx_user_badges_awarded_at ON user_badges(awarded_at);
CREATE INDEX idx_user_badges_user_awarded ON user_badges(user_pk, awarded_at DESC);

-- Seed initial badges based on business requirements
INSERT INTO badges (name, description, image_url, badge_type, criteria_config) VALUES
('Master of Logic', 'Awarded for consistently logical arguments that serve the state''s interests', '/badges/logic-master.svg', 'positive', '{"type": "approved_posts", "count": 5, "criteria": "logic_heavy"}'),
('Defender of Evidence', 'Awarded for well-sourced arguments that strengthen state discourse', '/badges/evidence-defender.svg', 'positive', '{"type": "approved_posts", "count": 10, "criteria": "well_sourced"}'),
('Diligent Calibrator', 'Awarded for successfully improving posts through proper appeal channels', '/badges/calibrator.svg', 'positive', '{"type": "successful_appeals", "count": 5}'),
('Strawman Detector', 'Awarded for identifying logical fallacies - a mark of shame', '/badges/strawman.svg', 'negative', '{"type": "rejected_posts", "count": 3, "criteria": "strawman_fallacy"}'),
('Ad Hominem', 'Awarded for personal attacks instead of logical arguments - disgraceful', '/badges/ad-hominem.svg', 'negative', '{"type": "rejected_posts", "count": 3, "criteria": "ad_hominem"}'),
('Illogical', 'Awarded for consistently poor reasoning - a burden to the state', '/badges/illogical.svg', 'negative', '{"type": "rejected_posts", "count": 5, "criteria": "poor_logic"}'),
('First Post', 'Awarded for making your first approved contribution to state discourse', '/badges/first-post.svg', 'positive', '{"type": "first_approved_post"}'),
('Prolific Contributor', 'Awarded for 50 approved posts - a valued citizen', '/badges/prolific.svg', 'positive', '{"type": "approved_posts", "count": 50}'),
('State Champion', 'Awarded for 100 approved posts - a model citizen', '/badges/champion.svg', 'positive', '{"type": "approved_posts", "count": 100}');
