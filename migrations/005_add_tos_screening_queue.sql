-- Migration: 005_add_tos_screening_queue.sql
-- Description: Add ToS screening queue table for dual-queue system
-- Author: joshszep
-- Date: 2025-08-18

-- step: create_post_tos_screening_queue_table
-- Create the ToS screening queue table
CREATE TABLE post_tos_screening_queue (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_pk UUID NOT NULL REFERENCES posts(pk) ON DELETE CASCADE,
    topic_pk UUID NOT NULL REFERENCES topics(pk) ON DELETE CASCADE,
    priority_score INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 0,
    position_in_queue INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    entered_queue_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    estimated_completion_at TIMESTAMP WITH TIME ZONE,
    worker_assigned_at TIMESTAMP WITH TIME ZONE,
    worker_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- step: create_tos_screening_queue_indexes
-- Indexes for efficient ToS screening queue operations
CREATE INDEX idx_post_tos_screening_queue_status ON post_tos_screening_queue(status);
CREATE INDEX idx_post_tos_screening_queue_priority ON post_tos_screening_queue(priority_score DESC, entered_queue_at ASC);
CREATE INDEX idx_post_tos_screening_queue_position ON post_tos_screening_queue(position_in_queue);
CREATE INDEX idx_post_tos_screening_queue_post_pk ON post_tos_screening_queue(post_pk);
CREATE INDEX idx_post_tos_screening_queue_worker ON post_tos_screening_queue(worker_id, status);

-- step: update_posts_default_status
-- Update posts table to use SUBMITTED as default status
ALTER TABLE posts ALTER COLUMN status SET DEFAULT 'submitted';

-- step: add_submitted_status_index
-- Add index for new SUBMITTED status
CREATE INDEX idx_posts_status_submitted ON posts(status) WHERE status = 'submitted';
