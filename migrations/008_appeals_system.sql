-- Migration: Appeals System
-- Description: Create appeals table and related indexes for the appeals workflow

-- Create appeals table
CREATE TABLE appeals (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appellant_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('topic', 'post', 'private_message')),
    content_pk UUID NOT NULL,
    appeal_type VARCHAR(30) NOT NULL CHECK (appeal_type IN (
        'topic_rejection',
        'post_rejection',
        'post_removal',
        'private_message_rejection',
        'sanction'
    )),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'under_review',
        'sustained',
        'denied',
        'withdrawn'
    )),

    -- Appeal details
    reason TEXT NOT NULL CHECK (LENGTH(reason) >= 20 AND LENGTH(reason) <= 1000),
    evidence TEXT CHECK (evidence IS NULL OR LENGTH(evidence) <= 2000),

    -- Review details
    reviewed_by UUID REFERENCES users(pk) ON DELETE SET NULL,
    review_notes TEXT CHECK (review_notes IS NULL OR LENGTH(review_notes) <= 1000),
    decision_reason TEXT CHECK (decision_reason IS NULL OR LENGTH(decision_reason) <= 1000),

    -- Timestamps
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,

    -- Rate limiting and priority
    previous_appeals_count INTEGER NOT NULL DEFAULT 0,
    priority_score INTEGER NOT NULL DEFAULT 0,

    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create indexes for efficient querying
CREATE INDEX idx_appeals_appellant_pk ON appeals(appellant_pk);
CREATE INDEX idx_appeals_content ON appeals(content_type, content_pk);
CREATE INDEX idx_appeals_status ON appeals(status);
CREATE INDEX idx_appeals_submitted_at ON appeals(submitted_at);
CREATE INDEX idx_appeals_reviewed_by ON appeals(reviewed_by);
CREATE INDEX idx_appeals_priority_queue ON appeals(status, priority_score DESC, submitted_at ASC)
    WHERE status IN ('pending', 'under_review');

-- Create composite index for eligibility checks
CREATE INDEX idx_appeals_eligibility ON appeals(appellant_pk, content_type, content_pk);
CREATE INDEX idx_appeals_daily_count ON appeals(appellant_pk, submitted_at);
CREATE INDEX idx_appeals_cooldown ON appeals(appellant_pk, status, reviewed_at)
    WHERE status = 'denied';

-- Create partial index for statistics
CREATE INDEX idx_appeals_stats ON appeals(status, submitted_at)
    WHERE submitted_at > NOW() - INTERVAL '30 days';

-- Add constraint to prevent duplicate appeals for same content
CREATE UNIQUE INDEX idx_appeals_unique_content ON appeals(appellant_pk, content_type, content_pk)
    WHERE status NOT IN ('denied', 'withdrawn');

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_appeals_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_appeals_updated_at
    BEFORE UPDATE ON appeals
    FOR EACH ROW
    EXECUTE FUNCTION update_appeals_updated_at();

-- Add constraint to ensure reviewed_at is set when status changes from pending
CREATE OR REPLACE FUNCTION validate_appeal_review()
RETURNS TRIGGER AS $$
BEGIN
    -- If status is changing to sustained or denied, ensure reviewed_at and reviewed_by are set
    IF NEW.status IN ('sustained', 'denied') AND OLD.status != NEW.status THEN
        IF NEW.reviewed_at IS NULL THEN
            NEW.reviewed_at = NOW();
        END IF;

        IF NEW.reviewed_by IS NULL THEN
            RAISE EXCEPTION 'reviewed_by must be set when appeal is decided';
        END IF;

        IF NEW.decision_reason IS NULL OR LENGTH(TRIM(NEW.decision_reason)) = 0 THEN
            RAISE EXCEPTION 'decision_reason must be provided when appeal is decided';
        END IF;
    END IF;

    -- If status is under_review, ensure reviewed_by is set
    IF NEW.status = 'under_review' AND OLD.status != NEW.status THEN
        IF NEW.reviewed_by IS NULL THEN
            RAISE EXCEPTION 'reviewed_by must be set when appeal is under review';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_appeal_review
    BEFORE UPDATE ON appeals
    FOR EACH ROW
    EXECUTE FUNCTION validate_appeal_review();

-- Add comments for documentation
COMMENT ON TABLE appeals IS 'Appeals submitted by users for moderation decisions';
COMMENT ON COLUMN appeals.appellant_pk IS 'User who submitted the appeal';
COMMENT ON COLUMN appeals.content_type IS 'Type of content being appealed (topic, post, private_message)';
COMMENT ON COLUMN appeals.content_pk IS 'ID of the specific content being appealed';
COMMENT ON COLUMN appeals.appeal_type IS 'Specific type of appeal (rejection, removal, sanction)';
COMMENT ON COLUMN appeals.status IS 'Current status of the appeal';
COMMENT ON COLUMN appeals.reason IS 'User provided reason for the appeal (20-1000 chars)';
COMMENT ON COLUMN appeals.evidence IS 'Additional evidence provided by user (optional, max 2000 chars)';
COMMENT ON COLUMN appeals.reviewed_by IS 'Moderator/admin who reviewed the appeal';
COMMENT ON COLUMN appeals.review_notes IS 'Internal notes from the reviewer';
COMMENT ON COLUMN appeals.decision_reason IS 'Reason for sustaining or denying the appeal';
COMMENT ON COLUMN appeals.priority_score IS 'Calculated priority score for queue ordering';
COMMENT ON COLUMN appeals.previous_appeals_count IS 'Number of previous appeals by this user (for rate limiting)';
