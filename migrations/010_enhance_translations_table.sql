-- Migration: 010_enhance_translations_table.sql
-- Description: Enhance translations table with quality scoring and provider tracking
-- Author: System
-- Date: 2025-08-20

-- step: add_translation_quality_fields
-- Add quality scoring and provider tracking to translations table
ALTER TABLE translations ADD COLUMN translation_quality_score REAL CHECK (translation_quality_score >= 0.0 AND translation_quality_score <= 1.0);
ALTER TABLE translations ADD COLUMN translation_provider VARCHAR(50) NOT NULL DEFAULT 'placeholder';
ALTER TABLE translations ADD COLUMN translation_metadata JSONB DEFAULT '{}';

-- step: create_translation_quality_indexes
-- Add indexes for translation quality queries
CREATE INDEX idx_translations_quality_score ON translations(translation_quality_score) WHERE translation_quality_score IS NOT NULL;
CREATE INDEX idx_translations_poor_quality ON translations(translation_quality_score ASC, created_at DESC) WHERE translation_quality_score < 0.7;
CREATE INDEX idx_translations_provider ON translations(translation_provider);

-- step: add_translation_constraints
-- Add constraint to ensure content_pk references exist (will be validated by application)
-- Note: We can't add foreign key constraints since content_pk can reference different tables

-- step: create_translation_stats_view
-- Create materialized view for translation statistics
CREATE MATERIALIZED VIEW translation_stats AS
SELECT
    COUNT(*) as total_translations,
    COUNT(DISTINCT language_code) as unique_languages,
    COUNT(DISTINCT content_pk) as translated_content_items,
    AVG(translation_quality_score) as avg_quality_score,
    COUNT(*) FILTER (WHERE translation_quality_score IS NOT NULL AND translation_quality_score < 0.7) as poor_quality_count,
    COUNT(*) FILTER (WHERE translation_quality_score IS NOT NULL AND translation_quality_score >= 0.9) as high_quality_count,
    MAX(created_at) as last_translation_at
FROM translations;

-- Create index for the materialized view
CREATE UNIQUE INDEX idx_translation_stats_singleton ON translation_stats((1));

-- step: add_translation_comments
-- Add documentation comments
COMMENT ON TABLE translations IS 'Stores original content and English translations for multilingual support';
COMMENT ON COLUMN translations.content_pk IS 'References the primary key of the content being translated (posts, topics, private_messages)';
COMMENT ON COLUMN translations.content_type IS 'Type of content being translated (post, topic, private_message)';
COMMENT ON COLUMN translations.language_code IS 'ISO language code of the original content';
COMMENT ON COLUMN translations.original_content IS 'Original content in the source language';
COMMENT ON COLUMN translations.translated_content IS 'English translation of the original content';
COMMENT ON COLUMN translations.translation_quality_score IS 'Quality score of the translation (0.0-1.0, higher is better)';
COMMENT ON COLUMN translations.translation_provider IS 'Service used for translation (e.g., openai, google, placeholder)';
COMMENT ON COLUMN translations.translation_metadata IS 'Additional metadata about the translation process';
