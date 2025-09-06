-- Migration: 002_schema_alignment_fixes.sql
-- Description: Fix schema/model misalignments identified in TODO.md analysis
-- Author: System
-- Date: 2025-01-06

-- Note: Most fixes were model-side changes to match existing schema
-- This migration only includes necessary schema changes where models couldn't be adjusted

-- No schema changes needed for appeals table - models were updated to match existing schema
-- No schema changes needed for sanctions table - models were updated to match existing schema
-- No schema changes needed for posts table - models were updated to match existing schema
-- No schema changes needed for post_tos_screening_queue - models were created to match existing schema

-- All alignment fixes were completed by updating Pydantic models to match the database schema
-- rather than changing the schema to match the models

-- This migration serves as documentation that schema alignment was completed
-- without requiring database structure changes

SELECT 'Schema alignment completed - all fixes were model-side adjustments' as status;
