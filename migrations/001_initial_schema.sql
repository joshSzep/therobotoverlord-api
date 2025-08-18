-- Migration: 001_initial_schema.sql
-- Description: Create initial database schema for The Robot Overlord
-- Author: System
-- Date: 2025-08-17

-- step: enable_extensions
-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "vector";

-- step: create_users_table
-- Core users table with role-based access control
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email CITEXT NOT NULL UNIQUE,
    google_id VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('citizen', 'moderator', 'admin', 'superadmin')) DEFAULT 'citizen',
    loyalty_score INTEGER DEFAULT 0, -- Cached score from proprietary algorithm, only public metric
    is_banned BOOLEAN DEFAULT FALSE,
    is_sanctioned BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- step: create_topics_table
-- Topics table for debate threads
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    author_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_by_overlord BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending_approval', 'approved', 'rejected')) DEFAULT 'pending_approval',
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- step: create_posts_table
-- Posts table for individual debate contributions
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    parent_post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL, -- Canonical English storage only
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
    overlord_feedback TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- Used for chronological display ordering
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE
);

-- step: create_tags_table
-- Tags table for content categorization
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- step: create_topic_tags_table
-- Junction table for topic-tag relationships
CREATE TABLE topic_tags (
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    assigned_by UUID NOT NULL REFERENCES users(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (topic_id, tag_id)
);

-- step: create_queue_tables
-- Topic creation queue for approval workflow
CREATE TABLE topic_creation_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    priority_score BIGINT NOT NULL, -- Timestamp + priority offset for ordering
    priority INTEGER DEFAULT 0,
    position_in_queue INTEGER NOT NULL, -- Calculated queue position for user display
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed')) DEFAULT 'pending',
    entered_queue_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    estimated_completion_at TIMESTAMP WITH TIME ZONE,
    worker_assigned_at TIMESTAMP WITH TIME ZONE,
    worker_id VARCHAR(255)
);

-- Post moderation queue for evaluation workflow
CREATE TABLE post_moderation_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    priority_score BIGINT NOT NULL, -- Timestamp + priority offset for ordering
    priority INTEGER DEFAULT 0,
    position_in_queue INTEGER NOT NULL, -- Calculated queue position for user display
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed')) DEFAULT 'pending',
    entered_queue_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    estimated_completion_at TIMESTAMP WITH TIME ZONE,
    worker_assigned_at TIMESTAMP WITH TIME ZONE,
    worker_id VARCHAR(255)
);

-- step: create_private_messages_table
-- Private messages between users
CREATE TABLE private_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
    overlord_feedback TEXT,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE
);

-- Private message queue for review workflow
CREATE TABLE private_message_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES private_messages(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(255) NOT NULL, -- Format: "users_{min_user_id}_{max_user_id}"
    priority_score BIGINT NOT NULL, -- Timestamp + priority offset for ordering
    priority INTEGER DEFAULT 0,
    position_in_queue INTEGER NOT NULL, -- Calculated queue position for user display
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed')) DEFAULT 'pending',
    entered_queue_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    estimated_completion_at TIMESTAMP WITH TIME ZONE,
    worker_assigned_at TIMESTAMP WITH TIME ZONE,
    worker_id VARCHAR(255)
);

-- step: create_governance_tables
-- Appeals table for human oversight
CREATE TABLE appeals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    appellant_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'sustained', 'denied')) DEFAULT 'pending',
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Flags table for content reporting
CREATE TABLE flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    flagger_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'sustained', 'dismissed')) DEFAULT 'pending',
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT flags_content_check CHECK (
        (post_id IS NOT NULL AND topic_id IS NULL) OR 
        (post_id IS NULL AND topic_id IS NOT NULL)
    )
);

-- Sanctions table for user penalties
CREATE TABLE sanctions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('posting_freeze', 'rate_limit')),
    applied_by UUID NOT NULL REFERENCES users(id),
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    reason TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- step: create_gamification_tables
-- Badges table for achievements
CREATE TABLE badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User badges junction table
CREATE TABLE user_badges (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id UUID NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    awarded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    awarded_for_post_id UUID REFERENCES posts(id),
    PRIMARY KEY (user_id, badge_id, awarded_at)
);

-- step: create_event_sourcing_tables
-- Moderation events for event-sourced loyalty scoring
CREATE TABLE moderation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- 'topic_moderated', 'post_moderated', 'private_message_moderated', etc.
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('topic', 'post', 'private_message')),
    content_id UUID NOT NULL, -- references posts.id, topics.id, or private_messages.id
    outcome VARCHAR(20) NOT NULL CHECK (outcome IN ('approved', 'rejected')), -- moderation result
    moderator_id UUID REFERENCES users(id), -- NULL for AI moderation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- step: create_multilingual_table
-- Translations table for multilingual support
CREATE TABLE translations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL, -- References posts.id, topics.id, or private_messages.id
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('post', 'topic', 'private_message')),
    language_code VARCHAR(10) NOT NULL, -- ISO language code
    original_content TEXT NOT NULL, -- Original submission before translation
    translated_content TEXT NOT NULL, -- English translation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(content_id, content_type, language_code)
);

-- step: create_indexes
-- Performance indexes for posts
CREATE INDEX idx_posts_topic_submission_order ON posts(topic_id, submitted_at);

-- Queue indexes
CREATE INDEX idx_topic_queue_priority_score ON topic_creation_queue(priority_score);
CREATE INDEX idx_topic_queue_status ON topic_creation_queue(status);
CREATE INDEX idx_topic_queue_topic ON topic_creation_queue(topic_id);
CREATE INDEX idx_topic_queue_position ON topic_creation_queue(position_in_queue);

CREATE INDEX idx_post_queue_topic_priority ON post_moderation_queue(topic_id, priority_score);
CREATE INDEX idx_post_queue_status ON post_moderation_queue(status);
CREATE INDEX idx_post_queue_post ON post_moderation_queue(post_id);
CREATE INDEX idx_post_queue_position ON post_moderation_queue(position_in_queue);

CREATE INDEX idx_message_queue_conv_priority ON private_message_queue(conversation_id, priority_score DESC, entered_queue_at ASC);
CREATE INDEX idx_message_queue_status ON private_message_queue(status);
CREATE INDEX idx_message_queue_message ON private_message_queue(message_id);
CREATE INDEX idx_message_queue_conv_position ON private_message_queue(conversation_id, position_in_queue);

-- Flags indexes
CREATE INDEX idx_flags_post_id ON flags(post_id) WHERE post_id IS NOT NULL;
CREATE INDEX idx_flags_topic_id ON flags(topic_id) WHERE topic_id IS NOT NULL;
CREATE INDEX idx_flags_flagger_id ON flags(flagger_id);
CREATE INDEX idx_flags_status ON flags(status);
CREATE INDEX idx_flags_reviewed_by ON flags(reviewed_by) WHERE reviewed_by IS NOT NULL;
CREATE INDEX idx_flags_created_at ON flags(created_at);

-- Moderation events indexes
CREATE INDEX idx_moderation_events_user_events ON moderation_events(user_id, created_at DESC);
CREATE INDEX idx_moderation_events_content ON moderation_events(content_type, content_id);
CREATE INDEX idx_moderation_events_event_type ON moderation_events(event_type);
CREATE INDEX idx_moderation_events_outcome_content ON moderation_events(outcome, content_type);

-- Users performance indexes
CREATE INDEX idx_users_loyalty_score_desc ON users(loyalty_score DESC) WHERE loyalty_score > 0;
CREATE INDEX idx_users_loyalty_username ON users(loyalty_score DESC, username) WHERE loyalty_score > 0;
CREATE INDEX idx_users_username ON users(username) WHERE loyalty_score > 0;
CREATE INDEX idx_users_created_at ON users(created_at);

-- Translations indexes
CREATE INDEX idx_translations_content ON translations(content_type, content_id);
CREATE INDEX idx_translations_language ON translations(language_code);

-- step: create_materialized_view
-- User leaderboard materialized view for performance
CREATE MATERIALIZED VIEW user_leaderboard AS
SELECT 
    u.id as user_id,
    u.username,
    u.loyalty_score,
    ROW_NUMBER() OVER (ORDER BY u.loyalty_score DESC, u.created_at ASC) as rank,
    CASE 
        WHEN ROW_NUMBER() OVER (ORDER BY u.loyalty_score DESC, u.created_at ASC) <= 
             (SELECT COUNT(*) * 0.1 FROM users WHERE loyalty_score > 0) 
        THEN true 
        ELSE false 
    END as can_create_topics,
    u.created_at,
    u.updated_at
FROM users u
WHERE u.loyalty_score > 0
ORDER BY u.loyalty_score DESC, u.created_at ASC;

-- Indexes for materialized view
CREATE UNIQUE INDEX idx_leaderboard_user_id ON user_leaderboard(user_id);
CREATE INDEX idx_leaderboard_rank ON user_leaderboard(rank);
CREATE INDEX idx_leaderboard_score ON user_leaderboard(loyalty_score DESC);
CREATE INDEX idx_leaderboard_topic_creators ON user_leaderboard(can_create_topics) WHERE can_create_topics = true;
