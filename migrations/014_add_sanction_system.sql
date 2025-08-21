-- Add sanctions system for user moderation enforcement
-- Migration: 014_add_sanction_system.sql

-- Create sanctions table
CREATE TABLE sanctions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('warning', 'temporary_ban', 'permanent_ban', 'post_restriction', 'topic_restriction')),
    applied_by_pk UUID NOT NULL REFERENCES users(pk) ON DELETE RESTRICT,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    reason TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX idx_sanctions_user_pk ON sanctions(user_pk);
CREATE INDEX idx_sanctions_type ON sanctions(type);
CREATE INDEX idx_sanctions_is_active ON sanctions(is_active);
CREATE INDEX idx_sanctions_applied_at ON sanctions(applied_at);
CREATE INDEX idx_sanctions_expires_at ON sanctions(expires_at) WHERE expires_at IS NOT NULL;

-- Create composite index for active sanctions by user
CREATE INDEX idx_sanctions_user_active ON sanctions(user_pk, is_active) WHERE is_active = TRUE;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_sanctions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sanctions_updated_at
    BEFORE UPDATE ON sanctions
    FOR EACH ROW
    EXECUTE FUNCTION update_sanctions_updated_at();

-- Add comments for documentation
COMMENT ON TABLE sanctions IS 'User sanctions for moderation enforcement';
COMMENT ON COLUMN sanctions.pk IS 'Primary key for the sanction';
COMMENT ON COLUMN sanctions.user_pk IS 'User who received the sanction';
COMMENT ON COLUMN sanctions.type IS 'Type of sanction applied';
COMMENT ON COLUMN sanctions.applied_by_pk IS 'Moderator/admin who applied the sanction';
COMMENT ON COLUMN sanctions.applied_at IS 'When the sanction was applied';
COMMENT ON COLUMN sanctions.expires_at IS 'When the sanction expires (NULL for permanent)';
COMMENT ON COLUMN sanctions.reason IS 'Reason for the sanction';
COMMENT ON COLUMN sanctions.is_active IS 'Whether the sanction is currently active';
