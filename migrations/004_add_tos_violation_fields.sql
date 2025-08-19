-- Migration: 004_add_tos_violation_fields.sql
-- Description: Add ToS violation tracking fields to posts table
-- Author: joshszep
-- Date: 2025-08-18

-- step: add_tos_violation_fields_to_posts
-- Add rejection_reason and tos_violation fields to posts table for ToS screening
ALTER TABLE posts 
ADD COLUMN rejection_reason TEXT,
ADD COLUMN tos_violation BOOLEAN DEFAULT FALSE;

-- step: add_in_transit_status_support
-- Update posts table to support the new IN_TRANSIT status
-- Note: The ContentStatus enum is handled in the application layer
-- No database constraint changes needed as we use VARCHAR for status

-- step: create_tos_violation_indexes
-- Indexes for efficient querying of ToS violations and rejection reasons
CREATE INDEX idx_posts_tos_violation ON posts(tos_violation) WHERE tos_violation = TRUE;
CREATE INDEX idx_posts_status_in_transit ON posts(status) WHERE status = 'in_transit';
CREATE INDEX idx_posts_rejection_reason ON posts(rejection_reason) WHERE rejection_reason IS NOT NULL;
