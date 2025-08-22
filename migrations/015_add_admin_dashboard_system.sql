-- Migration: Add Admin Dashboard System
-- Description: Creates tables for admin dashboard functionality including audit trail, snapshots, and announcements

-- Admin Actions table for audit trail
CREATE TABLE admin_actions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_pk UUID,
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for admin actions
CREATE INDEX idx_admin_actions_admin_pk ON admin_actions(admin_pk);
CREATE INDEX idx_admin_actions_action_type ON admin_actions(action_type);
CREATE INDEX idx_admin_actions_target ON admin_actions(target_type, target_pk);
CREATE INDEX idx_admin_actions_created_at ON admin_actions(created_at DESC);

-- Dashboard Snapshots table for historical data
CREATE TABLE dashboard_snapshots (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_type VARCHAR(20) NOT NULL CHECK (snapshot_type IN ('hourly', 'daily', 'weekly', 'monthly')),
    metrics_data JSONB NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for dashboard snapshots
CREATE INDEX idx_dashboard_snapshots_type ON dashboard_snapshots(snapshot_type);
CREATE INDEX idx_dashboard_snapshots_period ON dashboard_snapshots(period_start, period_end);
CREATE INDEX idx_dashboard_snapshots_generated_at ON dashboard_snapshots(generated_at DESC);

-- System Announcements table
CREATE TABLE system_announcements (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    announcement_type VARCHAR(20) NOT NULL CHECK (announcement_type IN ('maintenance', 'feature_update', 'policy_change', 'general', 'emergency')),
    created_by_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    target_roles TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for system announcements
CREATE INDEX idx_system_announcements_active ON system_announcements(is_active, expires_at);
CREATE INDEX idx_system_announcements_created_by ON system_announcements(created_by_pk);
CREATE INDEX idx_system_announcements_type ON system_announcements(announcement_type);
CREATE INDEX idx_system_announcements_created_at ON system_announcements(created_at DESC);

-- Comments for documentation
COMMENT ON TABLE admin_actions IS 'Audit trail of administrative actions performed by admins and moderators';
COMMENT ON TABLE dashboard_snapshots IS 'Historical snapshots of dashboard metrics for trend analysis';
COMMENT ON TABLE system_announcements IS 'System-wide announcements for users and administrators';

COMMENT ON COLUMN admin_actions.action_type IS 'Type of administrative action performed';
COMMENT ON COLUMN admin_actions.target_type IS 'Type of entity the action was performed on (user, post, topic, etc.)';
COMMENT ON COLUMN admin_actions.target_pk IS 'Primary key of the target entity';
COMMENT ON COLUMN admin_actions.metadata IS 'Additional metadata about the action in JSON format';

COMMENT ON COLUMN dashboard_snapshots.snapshot_type IS 'Frequency of the snapshot (hourly, daily, weekly, monthly)';
COMMENT ON COLUMN dashboard_snapshots.metrics_data IS 'Aggregated metrics data in JSON format';

COMMENT ON COLUMN system_announcements.target_roles IS 'Array of user roles this announcement is targeted at (empty means all roles)';
COMMENT ON COLUMN system_announcements.expires_at IS 'When the announcement expires (NULL means no expiration)';
