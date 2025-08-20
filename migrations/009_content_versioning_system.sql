-- Migration: Content Versioning and Restoration System
-- Description: Add content versioning tables for audit trail and content restoration with moderator editing
-- Depends: 008_appeals_system.sql

-- Content versions table for tracking all content changes
CREATE TABLE content_versions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type content_type_enum NOT NULL,
    content_pk UUID NOT NULL,
    version_number INTEGER NOT NULL,

    -- Original content fields
    original_title TEXT,
    original_content TEXT NOT NULL,
    original_description TEXT,

    -- Edited content fields
    edited_title TEXT,
    edited_content TEXT,
    edited_description TEXT,

    -- Edit metadata
    edited_by UUID REFERENCES users(pk),
    edit_reason TEXT,
    edit_type VARCHAR(50) NOT NULL DEFAULT 'appeal_restoration', -- 'appeal_restoration', 'moderator_edit', 'author_edit'

    -- Appeal context (if applicable)
    appeal_pk UUID REFERENCES appeals(pk),

    -- Audit trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_content_version UNIQUE(content_pk, version_number)
);

-- Indexes for content versions
CREATE INDEX idx_content_versions_content ON content_versions(content_pk);
CREATE INDEX idx_content_versions_appeal ON content_versions(appeal_pk);
CREATE INDEX idx_content_versions_editor ON content_versions(edited_by);
CREATE INDEX idx_content_versions_type ON content_versions(content_type);
CREATE INDEX idx_content_versions_created ON content_versions(created_at);

-- Enhanced content restorations table
CREATE TABLE content_restorations (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appeal_pk UUID NOT NULL REFERENCES appeals(pk),
    content_type content_type_enum NOT NULL,
    content_pk UUID NOT NULL,
    content_version_pk UUID NOT NULL REFERENCES content_versions(pk),

    restored_by UUID NOT NULL REFERENCES users(pk),
    restoration_reason TEXT,
    original_status VARCHAR(50) NOT NULL,
    restored_status VARCHAR(50) NOT NULL,

    -- Editing metadata
    content_was_edited BOOLEAN DEFAULT FALSE,
    edit_summary TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_appeal_content_restoration UNIQUE(appeal_pk, content_pk)
);

-- Indexes for content restorations
CREATE INDEX idx_content_restorations_content ON content_restorations(content_pk);
CREATE INDEX idx_content_restorations_restorer ON content_restorations(restored_by);
CREATE INDEX idx_content_restorations_appeal ON content_restorations(appeal_pk);
CREATE INDEX idx_content_restorations_created ON content_restorations(created_at);

-- Add new columns to existing appeals table for restoration tracking
ALTER TABLE appeals ADD COLUMN restoration_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE appeals ADD COLUMN restoration_completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appeals ADD COLUMN restoration_metadata JSONB;

-- Create index for restoration status queries
CREATE INDEX idx_appeals_restoration_completed ON appeals(restoration_completed);

-- Function to get next version number for content
CREATE OR REPLACE FUNCTION get_next_version_number(p_content_pk UUID)
RETURNS INTEGER AS $$
DECLARE
    next_version INTEGER;
BEGIN
    SELECT COALESCE(MAX(version_number), 0) + 1
    INTO next_version
    FROM content_versions
    WHERE content_pk = p_content_pk;

    RETURN next_version;
END;
$$ LANGUAGE plpgsql;

-- Function to create content version with automatic version numbering
CREATE OR REPLACE FUNCTION create_content_version(
    p_content_type content_type_enum,
    p_content_pk UUID,
    p_original_title TEXT DEFAULT NULL,
    p_original_content TEXT DEFAULT NULL,
    p_original_description TEXT DEFAULT NULL,
    p_edited_title TEXT DEFAULT NULL,
    p_edited_content TEXT DEFAULT NULL,
    p_edited_description TEXT DEFAULT NULL,
    p_edited_by UUID DEFAULT NULL,
    p_edit_reason TEXT DEFAULT NULL,
    p_edit_type VARCHAR(50) DEFAULT 'appeal_restoration',
    p_appeal_pk UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    version_pk UUID;
    next_version INTEGER;
BEGIN
    -- Get next version number
    next_version := get_next_version_number(p_content_pk);

    -- Insert new version record
    INSERT INTO content_versions (
        content_type,
        content_pk,
        version_number,
        original_title,
        original_content,
        original_description,
        edited_title,
        edited_content,
        edited_description,
        edited_by,
        edit_reason,
        edit_type,
        appeal_pk
    ) VALUES (
        p_content_type,
        p_content_pk,
        next_version,
        p_original_title,
        p_original_content,
        p_original_description,
        p_edited_title,
        p_edited_content,
        p_edited_description,
        p_edited_by,
        p_edit_reason,
        p_edit_type,
        p_appeal_pk
    ) RETURNING pk INTO version_pk;

    RETURN version_pk;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE content_versions IS 'Tracks all versions of content with full audit trail for moderator edits and restorations';
COMMENT ON TABLE content_restorations IS 'Records content restoration events from sustained appeals with editing metadata';
COMMENT ON FUNCTION get_next_version_number(UUID) IS 'Returns the next version number for a given content item';
COMMENT ON FUNCTION create_content_version IS 'Creates a new content version with automatic version numbering and full audit trail';
