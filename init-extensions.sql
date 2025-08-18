-- Initialize required PostgreSQL extensions for The Robot Overlord
-- This script runs automatically when the Docker container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "vector";
