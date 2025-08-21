-- Migration: Add Tag System
-- Description: Create tags and topic_tags tables for content organization system

-- Tags table for tag definitions
CREATE TABLE tags (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Topic tags junction table
CREATE TABLE topic_tags (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_pk UUID NOT NULL REFERENCES topics(pk) ON DELETE CASCADE,
    tag_pk UUID NOT NULL REFERENCES tags(pk) ON DELETE CASCADE,
    assigned_by_pk UUID NOT NULL REFERENCES users(pk),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(topic_pk, tag_pk) -- One tag per topic
);

-- Indexes for performance
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_created_at ON tags(created_at);

CREATE INDEX idx_topic_tags_topic ON topic_tags(topic_pk);
CREATE INDEX idx_topic_tags_tag ON topic_tags(tag_pk);
CREATE INDEX idx_topic_tags_assigned_by ON topic_tags(assigned_by_pk);
CREATE INDEX idx_topic_tags_assigned_at ON topic_tags(assigned_at);
CREATE INDEX idx_topic_tags_topic_assigned ON topic_tags(topic_pk, assigned_at DESC);

-- Seed initial tags based on business requirements
INSERT INTO tags (name, description) VALUES
('Politics', 'Political discourse and governance topics'),
('Economics', 'Economic policy and financial discussions'),
('Technology', 'Technology, innovation, and digital society'),
('Environment', 'Environmental policy and climate discussions'),
('Healthcare', 'Healthcare policy and medical topics'),
('Education', 'Educational policy and academic discourse'),
('Social Issues', 'Social justice and community topics'),
('International', 'Foreign policy and international relations'),
('Philosophy', 'Philosophical and ethical discussions'),
('Science', 'Scientific research and evidence-based topics'),
('Law', 'Legal system and jurisprudence'),
('Culture', 'Cultural and artistic discussions'),
('Defense', 'National security and defense policy'),
('Infrastructure', 'Public works and infrastructure policy'),
('Immigration', 'Immigration policy and border security');
