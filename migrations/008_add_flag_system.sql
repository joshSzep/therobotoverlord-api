-- Migration: Add flag system for content reporting and moderation
-- Created: 2025-01-21
-- Description: Creates flags table and related indexes for community content flagging

-- Create flags table
CREATE TABLE flags (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_pk UUID REFERENCES posts(pk) ON DELETE CASCADE,
    topic_pk UUID REFERENCES topics(pk) ON DELETE CASCADE,
    flagger_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed', 'upheld')),
    reviewed_by_pk UUID REFERENCES users(pk),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure exactly one content type is flagged
    CONSTRAINT flags_content_check CHECK (
        (post_pk IS NOT NULL AND topic_pk IS NULL) OR
        (post_pk IS NULL AND topic_pk IS NOT NULL)
    )
);

-- Create indexes for efficient querying
CREATE INDEX idx_flags_post_pk ON flags(post_pk) WHERE post_pk IS NOT NULL;
CREATE INDEX idx_flags_topic_pk ON flags(topic_pk) WHERE topic_pk IS NOT NULL;
CREATE INDEX idx_flags_flagger_pk ON flags(flagger_pk);
CREATE INDEX idx_flags_status ON flags(status);
CREATE INDEX idx_flags_reviewed_by_pk ON flags(reviewed_by_pk) WHERE reviewed_by_pk IS NOT NULL;
CREATE INDEX idx_flags_created_at ON flags(created_at);
CREATE INDEX idx_flags_reviewed_at ON flags(reviewed_at) WHERE reviewed_at IS NOT NULL;

-- Create composite index for moderation queue queries
CREATE INDEX idx_flags_status_created ON flags(status, created_at) WHERE status = 'pending';

-- Create composite index for user flag history
CREATE INDEX idx_flags_flagger_status_reviewed ON flags(flagger_pk, status, reviewed_at)
WHERE status IN ('dismissed', 'upheld') AND reviewed_at IS NOT NULL;

-- Add comments for documentation
COMMENT ON TABLE flags IS 'Community content flagging system for posts and topics';
COMMENT ON COLUMN flags.pk IS 'Primary key for flag record';
COMMENT ON COLUMN flags.post_pk IS 'Reference to flagged post (mutually exclusive with topic_pk)';
COMMENT ON COLUMN flags.topic_pk IS 'Reference to flagged topic (mutually exclusive with post_pk)';
COMMENT ON COLUMN flags.flagger_pk IS 'User who submitted the flag';
COMMENT ON COLUMN flags.reason IS 'User-provided reason for flagging the content';
COMMENT ON COLUMN flags.status IS 'Current status of the flag review process';
COMMENT ON COLUMN flags.reviewed_by_pk IS 'Moderator who reviewed the flag';
COMMENT ON COLUMN flags.reviewed_at IS 'Timestamp when flag was reviewed';
COMMENT ON COLUMN flags.review_notes IS 'Moderator notes from flag review';
COMMENT ON CONSTRAINT flags_content_check ON flags IS 'Ensures exactly one content type is flagged per record';
