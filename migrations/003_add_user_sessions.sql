-- Migration: 003_add_user_sessions.sql
-- Description: Add user sessions table for refresh token management
-- Author: System
-- Date: 2025-08-18

-- step: create_user_sessions_table
-- User sessions table for refresh token management and session tracking
CREATE TABLE user_sessions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_ip INET,
    last_used_user_agent TEXT,
    is_revoked BOOLEAN DEFAULT FALSE,
    reuse_detected BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    rotated_at TIMESTAMP WITH TIME ZONE
);

-- step: create_user_sessions_indexes
-- Indexes for user sessions table
CREATE INDEX idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX idx_user_sessions_user_pk ON user_sessions(user_pk);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_active ON user_sessions(user_pk, expires_at) WHERE is_revoked = FALSE;
CREATE INDEX idx_user_sessions_cleanup ON user_sessions(expires_at, is_revoked, revoked_at);
