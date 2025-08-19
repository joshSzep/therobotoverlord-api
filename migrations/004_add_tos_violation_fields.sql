-- Migration: 004_add_tos_violation_fields.sql
-- Description: Add rejection_reason field and TOS_VIOLATION status to posts table
-- Author: joshszep
-- Date: 2025-08-18

-- step: add_rejection_reason_column
-- Add rejection_reason column to posts table
ALTER TABLE posts ADD COLUMN rejection_reason TEXT;

-- step: create_rejection_indexes
-- Create indexes for efficient querying of rejected posts
CREATE INDEX idx_posts_rejection_reason ON posts(rejection_reason) WHERE rejection_reason IS NOT NULL;

-- step: add_tos_violation_status_index
-- Add index for TOS_VIOLATION status
CREATE INDEX idx_posts_status_tos_violation ON posts(status) WHERE status = 'tos_violation';

-- step: add_in_transit_index
-- Add index for IN_TRANSIT status for public viewing
CREATE INDEX idx_posts_status_in_transit ON posts(status) WHERE status = 'in_transit';
