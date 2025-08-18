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
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- step: create_posts_table
-- Posts table for individual debate contributions
CREATE TABLE posts (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_pk UUID NOT NULL REFERENCES topics(pk) ON DELETE CASCADE,
    parent_post_pk UUID REFERENCES posts(pk) ON DELETE CASCADE,
    author_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
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
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- step: create_topic_tags_table
-- Junction table for topic-tag relationships
CREATE TABLE topic_tags (
    topic_pk UUID NOT NULL REFERENCES topics(pk) ON DELETE CASCADE,
    tag_pk UUID NOT NULL REFERENCES tags(pk) ON DELETE CASCADE,
    assigned_by_pk UUID NOT NULL REFERENCES users(pk),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (topic_pk, tag_pk)
);

-- step: create_queue_tables
-- Topic creation queue for approval workflow
CREATE TABLE topic_creation_queue (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_pk UUID NOT NULL REFERENCES topics(pk) ON DELETE CASCADE,
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
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_pk UUID NOT NULL REFERENCES posts(pk) ON DELETE CASCADE,
    topic_pk UUID NOT NULL REFERENCES topics(pk) ON DELETE CASCADE,
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
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    recipient_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
    overlord_feedback TEXT,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE
);

-- Private message queue for review workflow
CREATE TABLE private_message_queue (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_pk UUID NOT NULL REFERENCES private_messages(pk) ON DELETE CASCADE,
    sender_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    recipient_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
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
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_pk UUID NOT NULL REFERENCES posts(pk) ON DELETE CASCADE,
    appellant_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'sustained', 'denied')) DEFAULT 'pending',
    reviewed_by_pk UUID REFERENCES users(pk),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Flags table for content reporting
CREATE TABLE flags (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_pk UUID REFERENCES posts(pk) ON DELETE CASCADE,
    topic_pk UUID REFERENCES topics(pk) ON DELETE CASCADE,
    flagger_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'sustained', 'dismissed')) DEFAULT 'pending',
    reviewed_by_pk UUID REFERENCES users(pk),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT flags_content_check CHECK (
        (post_pk IS NOT NULL AND topic_pk IS NULL) OR
        (post_pk IS NULL AND topic_pk IS NOT NULL)
    )
);

-- Sanctions table for user penalties
CREATE TABLE sanctions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('posting_freeze', 'rate_limit')),
    applied_by_pk UUID NOT NULL REFERENCES users(pk),
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    reason TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- step: create_gamification_tables
-- Badges table for achievements
CREATE TABLE badges (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User badges junction table
CREATE TABLE user_badges (
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    badge_pk UUID NOT NULL REFERENCES badges(pk) ON DELETE CASCADE,
    awarded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    awarded_for_post_pk UUID REFERENCES posts(pk),
    PRIMARY KEY (user_pk, badge_pk, awarded_at)
);

-- step: create_event_sourcing_tables
-- Moderation events for event-sourced loyalty scoring
CREATE TABLE moderation_events (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- 'topic_moderated', 'post_moderated', 'private_message_moderated', etc.
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('topic', 'post', 'private_message')),
    content_pk UUID NOT NULL, -- references posts.pk, topics.pk, or private_messages.pk
    outcome VARCHAR(20) NOT NULL CHECK (outcome IN ('approved', 'rejected')), -- moderation result
    moderator_pk UUID REFERENCES users(pk), -- NULL for AI moderation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- step: create_multilingual_table
-- Translations table for multilingual support
CREATE TABLE translations (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_pk UUID NOT NULL, -- References posts.pk, topics.pk, or private_messages.pk
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('post', 'topic', 'private_message')),
    language_code VARCHAR(10) NOT NULL, -- ISO language code
    original_content TEXT NOT NULL, -- Original submission before translation
    translated_content TEXT NOT NULL, -- English translation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(content_pk, content_type, language_code)
);

-- step: create_indexes
-- Performance indexes for posts
CREATE INDEX idx_posts_topic_submission_order ON posts(topic_pk, submitted_at);

-- Queue indexes
CREATE INDEX idx_topic_queue_priority_score ON topic_creation_queue(priority_score);
CREATE INDEX idx_topic_queue_status ON topic_creation_queue(status);
CREATE INDEX idx_topic_queue_topic ON topic_creation_queue(topic_pk);
CREATE INDEX idx_topic_queue_position ON topic_creation_queue(position_in_queue);

CREATE INDEX idx_post_queue_topic_priority ON post_moderation_queue(topic_pk, priority_score);
CREATE INDEX idx_post_queue_status ON post_moderation_queue(status);
CREATE INDEX idx_post_queue_post ON post_moderation_queue(post_pk);
CREATE INDEX idx_post_queue_position ON post_moderation_queue(position_in_queue);

CREATE INDEX idx_message_queue_conv_priority ON private_message_queue(conversation_id, priority_score DESC, entered_queue_at ASC);
CREATE INDEX idx_message_queue_status ON private_message_queue(status);
CREATE INDEX idx_message_queue_message ON private_message_queue(message_pk);
CREATE INDEX idx_message_queue_conv_position ON private_message_queue(conversation_id, position_in_queue);

-- Flags indexes
CREATE INDEX idx_flags_post_pk ON flags(post_pk) WHERE post_pk IS NOT NULL;
CREATE INDEX idx_flags_topic_pk ON flags(topic_pk) WHERE topic_pk IS NOT NULL;
CREATE INDEX idx_flags_flagger_pk ON flags(flagger_pk);
CREATE INDEX idx_flags_status ON flags(status);
CREATE INDEX idx_flags_reviewed_by_pk ON flags(reviewed_by_pk) WHERE reviewed_by_pk IS NOT NULL;
CREATE INDEX idx_flags_created_at ON flags(created_at);

-- Moderation events indexes
CREATE INDEX idx_moderation_events_user_events ON moderation_events(user_pk, created_at DESC);
CREATE INDEX idx_moderation_events_content ON moderation_events(content_type, content_pk);
CREATE INDEX idx_moderation_events_event_type ON moderation_events(event_type);
CREATE INDEX idx_moderation_events_outcome_content ON moderation_events(outcome, content_type);

-- Users performance indexes
CREATE INDEX idx_users_loyalty_score_desc ON users(loyalty_score DESC) WHERE loyalty_score > 0;
CREATE INDEX idx_users_loyalty_username ON users(loyalty_score DESC, username) WHERE loyalty_score > 0;
CREATE INDEX idx_users_username ON users(username) WHERE loyalty_score > 0;
CREATE INDEX idx_users_created_at ON users(created_at);

-- Translations indexes
CREATE INDEX idx_translations_content ON translations(content_type, content_pk);
CREATE INDEX idx_translations_language ON translations(language_code);

-- step: create_materialized_view
-- User leaderboard materialized view for performance
CREATE MATERIALIZED VIEW user_leaderboard AS
SELECT
    u.pk as user_pk,
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
CREATE UNIQUE INDEX idx_leaderboard_user_pk ON user_leaderboard(user_pk);
CREATE INDEX idx_leaderboard_rank ON user_leaderboard(rank);
CREATE INDEX idx_leaderboard_score ON user_leaderboard(loyalty_score DESC);
CREATE INDEX idx_leaderboard_topic_creators ON user_leaderboard(can_create_topics) WHERE can_create_topics = true;
