-- Migration: 001_base_schema.sql
-- Description: Consolidated base schema for The Robot Overlord platform
-- Author: System
-- Date: 2025-08-30

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
CREATE TYPE content_type_enum AS ENUM ('topic', 'post', 'comment');

-- Core users table with role-based access control
CREATE TABLE users (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email CITEXT NOT NULL UNIQUE,
    google_id VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('citizen', 'moderator', 'admin', 'superadmin')) DEFAULT 'citizen',
    loyalty_score INTEGER DEFAULT 0,
    is_banned BOOLEAN DEFAULT FALSE,
    is_sanctioned BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- TOS violation fields
    tos_violation_count INTEGER DEFAULT 0,
    last_tos_violation_at TIMESTAMP WITH TIME ZONE,
    tos_violation_severity VARCHAR(20) CHECK (tos_violation_severity IN ('minor', 'moderate', 'severe')) DEFAULT 'minor'
);

-- User sessions table
CREATE TABLE user_sessions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Topics table for debate threads
CREATE TABLE topics (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    author_pk UUID REFERENCES users(pk) ON DELETE SET NULL,
    created_by_overlord BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending_approval', 'approved', 'rejected')) DEFAULT 'pending_approval',
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by UUID REFERENCES users(pk),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Posts table for individual debate contributions
CREATE TABLE posts (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_pk UUID NOT NULL REFERENCES topics(pk) ON DELETE CASCADE,
    parent_post_pk UUID REFERENCES posts(pk) ON DELETE CASCADE,
    author_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    content TEXT NOT NULL,
    post_number INTEGER NOT NULL,
    is_edited BOOLEAN DEFAULT FALSE,
    edit_count INTEGER DEFAULT 0,
    last_edited_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- TOS screening fields
    tos_status VARCHAR(20) DEFAULT 'pending_review' CHECK (tos_status IN ('pending_review', 'approved', 'flagged', 'rejected')),
    tos_reviewed_at TIMESTAMP WITH TIME ZONE,
    tos_reviewed_by UUID REFERENCES users(pk),
    tos_violation_reason TEXT,

    CONSTRAINT unique_post_number_per_topic UNIQUE(topic_pk, post_number)
);

-- TOS screening queue
CREATE TABLE post_tos_screening_queue (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_pk UUID NOT NULL REFERENCES posts(pk) ON DELETE CASCADE,
    priority INTEGER DEFAULT 1,
    assigned_to UUID REFERENCES users(pk),
    assigned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Post moderation queue
CREATE TABLE post_moderation_queue (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_pk UUID NOT NULL REFERENCES posts(pk) ON DELETE CASCADE,
    priority INTEGER DEFAULT 1,
    assigned_to UUID REFERENCES users(pk),
    assigned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Topic creation queue
CREATE TABLE topic_creation_queue (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    author_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    priority INTEGER DEFAULT 1,
    assigned_to UUID REFERENCES users(pk),
    assigned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Private messages table
CREATE TABLE private_messages (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    recipient_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    subject VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Private message queue
CREATE TABLE private_message_queue (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_pk UUID NOT NULL REFERENCES private_messages(pk) ON DELETE CASCADE,
    priority INTEGER DEFAULT 1,
    assigned_to UUID REFERENCES users(pk),
    assigned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Flags table for content flagging
CREATE TABLE flags (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flagger_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    flagged_content_type VARCHAR(20) NOT NULL CHECK (flagged_content_type IN ('post', 'topic', 'user')),
    flagged_content_pk UUID NOT NULL,
    flag_reason VARCHAR(100) NOT NULL,
    flag_description TEXT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'reviewed', 'dismissed', 'upheld')) DEFAULT 'pending',
    reviewed_by UUID REFERENCES users(pk),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Badges table
CREATE TABLE badges (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    badge_type VARCHAR(50) NOT NULL,
    criteria JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    image_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User badges table
CREATE TABLE user_badges (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    badge_pk UUID NOT NULL REFERENCES badges(pk) ON DELETE CASCADE,
    awarded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    awarded_by UUID REFERENCES users(pk),
    awarded_for_post_pk UUID REFERENCES posts(pk),
    awarded_for_topic_pk UUID REFERENCES topics(pk),

    CONSTRAINT unique_user_badge UNIQUE(user_pk, badge_pk)
);

-- Tags table
CREATE TABLE tags (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(7) DEFAULT '#007bff',
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(pk),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Topic tags table
CREATE TABLE topic_tags (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_pk UUID NOT NULL REFERENCES topics(pk) ON DELETE CASCADE,
    tag_pk UUID NOT NULL REFERENCES tags(pk) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(pk),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_topic_tag UNIQUE(topic_pk, tag_pk)
);

-- Sanctions table
CREATE TABLE sanctions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    sanction_type VARCHAR(50) NOT NULL CHECK (sanction_type IN ('warning', 'temporary_ban', 'permanent_ban', 'post_restriction', 'topic_restriction')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('minor', 'moderate', 'severe')) DEFAULT 'minor',
    applied_by_pk UUID REFERENCES users(pk),
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    reason TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Appeals table
CREATE TABLE appeals (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    sanction_pk UUID REFERENCES sanctions(pk) ON DELETE CASCADE,
    flag_pk UUID REFERENCES flags(pk) ON DELETE CASCADE,
    appeal_type VARCHAR(50) NOT NULL CHECK (appeal_type IN ('sanction_appeal', 'flag_appeal', 'content_restoration')),
    appeal_reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'under_review', 'approved', 'denied')) DEFAULT 'pending',
    reviewed_by UUID REFERENCES users(pk),
    review_notes TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    restoration_completed BOOLEAN DEFAULT FALSE,
    restoration_completed_at TIMESTAMP WITH TIME ZONE,
    restoration_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Appeal history table
CREATE TABLE appeal_history (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appeal_pk UUID NOT NULL REFERENCES appeals(pk) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    action_description TEXT,
    performed_by UUID REFERENCES users(pk),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Moderation events table
CREATE TABLE moderation_events (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    moderator_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('post', 'topic', 'user')),
    target_pk UUID NOT NULL,
    action_taken VARCHAR(100) NOT NULL,
    reason TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Translations table
CREATE TABLE translations (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('post', 'topic')),
    content_pk UUID NOT NULL,
    source_language VARCHAR(10) NOT NULL DEFAULT 'en',
    target_language VARCHAR(10) NOT NULL,
    original_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    translation_service VARCHAR(50) NOT NULL,
    confidence_score DECIMAL(3,2),
    quality_score DECIMAL(3,2),
    human_reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by UUID REFERENCES users(pk),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_translation UNIQUE(content_pk, content_type, target_language)
);

-- Loyalty score adjustments table
CREATE TABLE loyalty_score_adjustments (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    adjustment_type VARCHAR(50) NOT NULL,
    points_change INTEGER NOT NULL,
    reason TEXT,
    related_content_type VARCHAR(20),
    related_content_pk UUID,
    applied_by UUID REFERENCES users(pk),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Loyalty score history table
CREATE TABLE loyalty_score_history (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    old_score INTEGER NOT NULL,
    new_score INTEGER NOT NULL,
    change_reason TEXT,
    adjustment_pk UUID REFERENCES loyalty_score_adjustments(pk),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Loyalty score breakdown cache table
CREATE TABLE loyalty_score_breakdown_cache (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    component_name VARCHAR(100) NOT NULL,
    component_score INTEGER NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_user_component UNIQUE(user_pk, component_name)
);

-- Content versions table
CREATE TABLE content_versions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type content_type_enum NOT NULL,
    content_pk UUID NOT NULL,
    version_number INTEGER NOT NULL,
    original_title TEXT,
    original_content TEXT NOT NULL,
    original_description TEXT,
    edited_title TEXT,
    edited_content TEXT,
    edited_description TEXT,
    edited_by UUID REFERENCES users(pk),
    edit_reason TEXT,
    edit_type VARCHAR(50) NOT NULL DEFAULT 'appeal_restoration',
    appeal_pk UUID REFERENCES appeals(pk),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_content_version UNIQUE(content_pk, version_number)
);

-- Content restorations table
CREATE TABLE content_restorations (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type content_type_enum NOT NULL,
    content_pk UUID NOT NULL,
    version_pk UUID NOT NULL REFERENCES content_versions(pk),
    restored_by UUID NOT NULL REFERENCES users(pk),
    restoration_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RBAC: Roles table
CREATE TABLE roles (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RBAC: Permissions table
CREATE TABLE permissions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RBAC: Role permissions table
CREATE TABLE role_permissions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_pk UUID NOT NULL REFERENCES roles(pk) ON DELETE CASCADE,
    permission_pk UUID NOT NULL REFERENCES permissions(pk) ON DELETE CASCADE,

    CONSTRAINT unique_role_permission UNIQUE(role_pk, permission_pk)
);

-- RBAC: User roles table
CREATE TABLE user_roles (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    role_pk UUID NOT NULL REFERENCES roles(pk) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(pk),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT unique_user_role UNIQUE(user_pk, role_pk)
);

-- RBAC: User permissions table
CREATE TABLE user_permissions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    permission_pk UUID NOT NULL REFERENCES permissions(pk) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(pk),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT unique_user_permission UNIQUE(user_pk, permission_pk)
);

-- Admin actions table
CREATE TABLE admin_actions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_pk UUID,
    description TEXT NOT NULL,
    metadata JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Dashboard snapshots table
CREATE TABLE dashboard_snapshots (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_type VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    created_by UUID REFERENCES users(pk),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System announcements table
CREATE TABLE system_announcements (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    announcement_type VARCHAR(50) NOT NULL DEFAULT 'general',
    target_roles TEXT[] DEFAULT ARRAY['citizen', 'moderator', 'admin', 'superadmin'],
    is_active BOOLEAN DEFAULT TRUE,
    starts_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ends_at TIMESTAMP WITH TIME ZONE,
    created_by UUID NOT NULL REFERENCES users(pk),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Overlord chat messages table
CREATE TABLE overlord_chat_messages (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    message TEXT NOT NULL,
    response TEXT,
    message_type VARCHAR(50) DEFAULT 'general',
    is_processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Leaderboard snapshots table
CREATE TABLE leaderboard_snapshots (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    loyalty_score INTEGER NOT NULL,
    post_count INTEGER NOT NULL,
    topic_count INTEGER NOT NULL,
    badge_count INTEGER NOT NULL,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_user_snapshot_date UNIQUE(user_pk, snapshot_date)
);

-- Leaderboard cache table
CREATE TABLE leaderboard_cache (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(255) NOT NULL UNIQUE,
    cache_data JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Leaderboard materialized view
CREATE MATERIALIZED VIEW leaderboard AS
SELECT
    u.pk as user_pk,
    u.username,
    u.loyalty_score,
    COUNT(DISTINCT p.pk) as post_count,
    COUNT(DISTINCT t.pk) as topic_count,
    COUNT(DISTINCT ub.pk) as badge_count,
    ROW_NUMBER() OVER (ORDER BY u.loyalty_score DESC, COUNT(DISTINCT p.pk) DESC) as rank
FROM users u
LEFT JOIN posts p ON u.pk = p.author_pk
LEFT JOIN topics t ON u.pk = t.author_pk
LEFT JOIN user_badges ub ON u.pk = ub.user_pk
WHERE u.is_banned = FALSE
GROUP BY u.pk, u.username, u.loyalty_score
ORDER BY u.loyalty_score DESC, COUNT(DISTINCT p.pk) DESC;

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_loyalty_score ON users(loyalty_score DESC);
CREATE INDEX idx_users_is_banned ON users(is_banned);
CREATE INDEX idx_users_created_at ON users(created_at);

CREATE INDEX idx_user_sessions_user_pk ON user_sessions(user_pk);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);

CREATE INDEX idx_topics_author ON topics(author_pk);
CREATE INDEX idx_topics_status ON topics(status);
CREATE INDEX idx_topics_created_at ON topics(created_at DESC);

CREATE INDEX idx_posts_topic ON posts(topic_pk);
CREATE INDEX idx_posts_author ON posts(author_pk);
CREATE INDEX idx_posts_parent ON posts(parent_post_pk);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_posts_tos_status ON posts(tos_status);

CREATE INDEX idx_post_tos_queue_post ON post_tos_screening_queue(post_pk);
CREATE INDEX idx_post_tos_queue_priority ON post_tos_screening_queue(priority DESC);
CREATE INDEX idx_post_tos_queue_assigned ON post_tos_screening_queue(assigned_to);

CREATE INDEX idx_post_mod_queue_post ON post_moderation_queue(post_pk);
CREATE INDEX idx_post_mod_queue_priority ON post_moderation_queue(priority DESC);
CREATE INDEX idx_post_mod_queue_assigned ON post_moderation_queue(assigned_to);

CREATE INDEX idx_topic_queue_author ON topic_creation_queue(author_pk);
CREATE INDEX idx_topic_queue_priority ON topic_creation_queue(priority DESC);
CREATE INDEX idx_topic_queue_assigned ON topic_creation_queue(assigned_to);

CREATE INDEX idx_private_messages_sender ON private_messages(sender_pk);
CREATE INDEX idx_private_messages_recipient ON private_messages(recipient_pk);
CREATE INDEX idx_private_messages_created_at ON private_messages(created_at DESC);

CREATE INDEX idx_flags_flagger ON flags(flagger_pk);
CREATE INDEX idx_flags_content ON flags(flagged_content_type, flagged_content_pk);
CREATE INDEX idx_flags_status ON flags(status);
CREATE INDEX idx_flags_created_at ON flags(created_at DESC);

CREATE INDEX idx_badges_type ON badges(badge_type);
CREATE INDEX idx_badges_active ON badges(is_active);

CREATE INDEX idx_user_badges_user ON user_badges(user_pk);
CREATE INDEX idx_user_badges_badge ON user_badges(badge_pk);
CREATE INDEX idx_user_badges_awarded_at ON user_badges(awarded_at DESC);

CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_active ON tags(is_active);

CREATE INDEX idx_topic_tags_topic ON topic_tags(topic_pk);
CREATE INDEX idx_topic_tags_tag ON topic_tags(tag_pk);

CREATE INDEX idx_sanctions_user ON sanctions(user_pk);
CREATE INDEX idx_sanctions_type ON sanctions(sanction_type);
CREATE INDEX idx_sanctions_active ON sanctions(is_active);
CREATE INDEX idx_sanctions_expires ON sanctions(expires_at);

CREATE INDEX idx_appeals_user ON appeals(user_pk);
CREATE INDEX idx_appeals_sanction ON appeals(sanction_pk);
CREATE INDEX idx_appeals_flag ON appeals(flag_pk);
CREATE INDEX idx_appeals_status ON appeals(status);
CREATE INDEX idx_appeals_type ON appeals(appeal_type);
CREATE INDEX idx_appeals_created_at ON appeals(created_at DESC);
CREATE INDEX idx_appeals_restoration_completed ON appeals(restoration_completed);

CREATE INDEX idx_appeal_history_appeal ON appeal_history(appeal_pk);
CREATE INDEX idx_appeal_history_performed_by ON appeal_history(performed_by);
CREATE INDEX idx_appeal_history_created_at ON appeal_history(created_at DESC);

CREATE INDEX idx_moderation_events_moderator ON moderation_events(moderator_pk);
CREATE INDEX idx_moderation_events_target ON moderation_events(target_type, target_pk);
CREATE INDEX idx_moderation_events_created_at ON moderation_events(created_at DESC);

CREATE INDEX idx_translations_content ON translations(content_type, content_pk);
CREATE INDEX idx_translations_target_lang ON translations(target_language);
CREATE INDEX idx_translations_quality ON translations(quality_score DESC);

CREATE INDEX idx_loyalty_adjustments_user ON loyalty_score_adjustments(user_pk);
CREATE INDEX idx_loyalty_adjustments_type ON loyalty_score_adjustments(adjustment_type);
CREATE INDEX idx_loyalty_adjustments_created_at ON loyalty_score_adjustments(created_at DESC);

CREATE INDEX idx_loyalty_history_user ON loyalty_score_history(user_pk);
CREATE INDEX idx_loyalty_history_created_at ON loyalty_score_history(created_at DESC);

CREATE INDEX idx_content_versions_content ON content_versions(content_pk);
CREATE INDEX idx_content_versions_appeal ON content_versions(appeal_pk);
CREATE INDEX idx_content_versions_editor ON content_versions(edited_by);
CREATE INDEX idx_content_versions_type ON content_versions(content_type);

CREATE INDEX idx_content_restorations_content ON content_restorations(content_type, content_pk);
CREATE INDEX idx_content_restorations_version ON content_restorations(version_pk);
CREATE INDEX idx_content_restorations_restored_by ON content_restorations(restored_by);

CREATE INDEX idx_roles_name ON roles(name);
CREATE INDEX idx_roles_system ON roles(is_system_role);

CREATE INDEX idx_permissions_resource ON permissions(resource);
CREATE INDEX idx_permissions_action ON permissions(action);

CREATE INDEX idx_role_permissions_role ON role_permissions(role_pk);
CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_pk);

CREATE INDEX idx_user_roles_user ON user_roles(user_pk);
CREATE INDEX idx_user_roles_role ON user_roles(role_pk);

CREATE INDEX idx_user_permissions_user ON user_permissions(user_pk);
CREATE INDEX idx_user_permissions_permission ON user_permissions(permission_pk);

CREATE INDEX idx_admin_actions_admin ON admin_actions(admin_pk);
CREATE INDEX idx_admin_actions_type ON admin_actions(action_type);
CREATE INDEX idx_admin_actions_target ON admin_actions(target_type, target_pk);
CREATE INDEX idx_admin_actions_created_at ON admin_actions(created_at DESC);

CREATE INDEX idx_dashboard_snapshots_type ON dashboard_snapshots(snapshot_type);
CREATE INDEX idx_dashboard_snapshots_created_at ON dashboard_snapshots(created_at DESC);

CREATE INDEX idx_system_announcements_active ON system_announcements(is_active);
CREATE INDEX idx_system_announcements_type ON system_announcements(announcement_type);
CREATE INDEX idx_system_announcements_starts_at ON system_announcements(starts_at);

CREATE INDEX idx_overlord_chat_user ON overlord_chat_messages(user_pk);
CREATE INDEX idx_overlord_chat_processed ON overlord_chat_messages(is_processed);
CREATE INDEX idx_overlord_chat_created_at ON overlord_chat_messages(created_at DESC);

CREATE INDEX idx_leaderboard_snapshots_user ON leaderboard_snapshots(user_pk);
CREATE INDEX idx_leaderboard_snapshots_date ON leaderboard_snapshots(snapshot_date DESC);
CREATE INDEX idx_leaderboard_snapshots_rank ON leaderboard_snapshots(rank);

CREATE INDEX idx_leaderboard_cache_key ON leaderboard_cache(cache_key);
CREATE INDEX idx_leaderboard_cache_expires ON leaderboard_cache(expires_at);

-- Create unique index on leaderboard materialized view
CREATE UNIQUE INDEX idx_leaderboard_user_pk ON leaderboard(user_pk);

-- Create GIN indexes for JSONB columns
CREATE INDEX idx_admin_actions_metadata_gin ON admin_actions USING GIN(metadata);
CREATE INDEX idx_dashboard_snapshots_data_gin ON dashboard_snapshots USING GIN(data);
CREATE INDEX idx_appeals_restoration_metadata_gin ON appeals USING GIN(restoration_metadata);
CREATE INDEX idx_appeal_history_metadata_gin ON appeal_history USING GIN(metadata);

-- Create text search indexes
CREATE INDEX idx_posts_content_search ON posts USING GIN(to_tsvector('english', content));
CREATE INDEX idx_topics_title_search ON topics USING GIN(to_tsvector('english', title));
CREATE INDEX idx_topics_description_search ON topics USING GIN(to_tsvector('english', description));

-- Create functions and triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_topics_updated_at BEFORE UPDATE ON topics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sanctions_updated_at BEFORE UPDATE ON sanctions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_appeals_updated_at BEFORE UPDATE ON appeals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to refresh leaderboard
CREATE OR REPLACE FUNCTION refresh_leaderboard()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY leaderboard;
END;
$$ LANGUAGE plpgsql;

-- Function to create content version
CREATE OR REPLACE FUNCTION create_content_version(
    p_content_type content_type_enum,
    p_content_pk UUID,
    p_original_content TEXT,
    p_edited_by UUID DEFAULT NULL,
    p_edit_reason TEXT DEFAULT NULL,
    p_appeal_pk UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_version_number INTEGER;
    v_version_pk UUID;
BEGIN
    -- Get next version number
    SELECT COALESCE(MAX(version_number), 0) + 1
    INTO v_version_number
    FROM content_versions
    WHERE content_pk = p_content_pk;

    -- Insert new version
    INSERT INTO content_versions (
        content_type, content_pk, version_number, original_content,
        edited_by, edit_reason, appeal_pk
    ) VALUES (
        p_content_type, p_content_pk, v_version_number, p_original_content,
        p_edited_by, p_edit_reason, p_appeal_pk
    ) RETURNING pk INTO v_version_pk;

    RETURN v_version_pk;
END;
$$ LANGUAGE plpgsql;

-- Insert seed data
INSERT INTO roles (name, description, is_system_role) VALUES
('citizen', 'Basic user role with standard permissions', true),
('moderator', 'Moderator role with content moderation permissions', true),
('admin', 'Administrator role with system management permissions', true),
('superadmin', 'Super administrator with full system access', true),
('bot', 'Automated system bot role', true);

INSERT INTO permissions (name, description, resource, action) VALUES
-- User management permissions
('users.create', 'Create new users', 'users', 'create'),
('users.read', 'View user profiles', 'users', 'read'),
('users.update', 'Update user profiles', 'users', 'update'),
('users.delete', 'Delete user accounts', 'users', 'delete'),
('users.ban', 'Ban/unban users', 'users', 'ban'),
('users.moderate', 'Moderate user content', 'users', 'moderate'),

-- Topic permissions
('topics.create', 'Create new topics', 'topics', 'create'),
('topics.read', 'View topics', 'topics', 'read'),
('topics.update', 'Update topics', 'topics', 'update'),
('topics.delete', 'Delete topics', 'topics', 'delete'),
('topics.approve', 'Approve pending topics', 'topics', 'approve'),
('topics.moderate', 'Moderate topic content', 'topics', 'moderate'),

-- Post permissions
('posts.create', 'Create new posts', 'posts', 'create'),
('posts.read', 'View posts', 'posts', 'read'),
('posts.update', 'Update posts', 'posts', 'update'),
('posts.delete', 'Delete posts', 'posts', 'delete'),
('posts.moderate', 'Moderate post content', 'posts', 'moderate'),

-- Moderation permissions
('moderation.review_flags', 'Review flagged content', 'moderation', 'review_flags'),
('moderation.apply_sanctions', 'Apply sanctions to users', 'moderation', 'apply_sanctions'),
('moderation.review_appeals', 'Review user appeals', 'moderation', 'review_appeals'),
('moderation.manage_queue', 'Manage moderation queues', 'moderation', 'manage_queue'),

-- Admin permissions
('admin.system_settings', 'Manage system settings', 'admin', 'system_settings'),
('admin.user_management', 'Advanced user management', 'admin', 'user_management'),
('admin.content_management', 'Advanced content management', 'admin', 'content_management'),
('admin.analytics', 'View system analytics', 'admin', 'analytics'),
('admin.announcements', 'Manage system announcements', 'admin', 'announcements');

-- Assign permissions to roles
INSERT INTO role_permissions (role_pk, permission_pk)
SELECT r.pk, p.pk FROM roles r, permissions p
WHERE r.name = 'citizen' AND p.name IN ('topics.read', 'posts.read', 'posts.create', 'topics.create');

INSERT INTO role_permissions (role_pk, permission_pk)
SELECT r.pk, p.pk FROM roles r, permissions p
WHERE r.name = 'moderator' AND p.name LIKE '%moderate%' OR p.name LIKE 'moderation.%';

INSERT INTO role_permissions (role_pk, permission_pk)
SELECT r.pk, p.pk FROM roles r, permissions p
WHERE r.name = 'admin' AND p.name NOT LIKE 'admin.system_settings';

INSERT INTO role_permissions (role_pk, permission_pk)
SELECT r.pk, p.pk FROM roles r, permissions p
WHERE r.name = 'superadmin';

-- Create system user for automated processes
INSERT INTO users (email, google_id, username, role, loyalty_score, email_verified) VALUES
('system@therobotoverlord.com', 'system-bot-001', 'TheRobotOverlord', 'superadmin', 9999, true);

-- Insert default badges
INSERT INTO badges (name, description, badge_type, criteria) VALUES
('First Post', 'Awarded for creating your first post', 'milestone', '{"posts_created": 1}'),
('Active Participant', 'Awarded for creating 10 posts', 'milestone', '{"posts_created": 10}'),
('Topic Starter', 'Awarded for creating your first topic', 'milestone', '{"topics_created": 1}'),
('Debate Champion', 'Awarded for high-quality debate contributions', 'achievement', '{"quality_score": 85}'),
('Community Helper', 'Awarded for helping other users', 'social', '{"helpful_actions": 5}'),
('Loyal Citizen', 'Awarded for consistent platform engagement', 'loyalty', '{"days_active": 30}');

-- Insert default tags
INSERT INTO tags (name, description, color, created_by) VALUES
('Politics', 'Political discussions and debates', '#dc3545', (SELECT pk FROM users WHERE username = 'TheRobotOverlord')),
('Technology', 'Technology-related topics', '#007bff', (SELECT pk FROM users WHERE username = 'TheRobotOverlord')),
('Science', 'Scientific discussions and discoveries', '#28a745', (SELECT pk FROM users WHERE username = 'TheRobotOverlord')),
('Philosophy', 'Philosophical debates and discussions', '#6f42c1', (SELECT pk FROM users WHERE username = 'TheRobotOverlord')),
('Society', 'Social issues and cultural topics', '#fd7e14', (SELECT pk FROM users WHERE username = 'TheRobotOverlord')),
('Economics', 'Economic discussions and analysis', '#20c997', (SELECT pk FROM users WHERE username = 'TheRobotOverlord')),
('Environment', 'Environmental issues and climate change', '#198754', (SELECT pk FROM users WHERE username = 'TheRobotOverlord')),
('Education', 'Educational topics and learning', '#0dcaf0', (SELECT pk FROM users WHERE username = 'TheRobotOverlord'));
