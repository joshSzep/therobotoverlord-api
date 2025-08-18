-- Migration: 002_seed_data.sql
-- Description: Seed initial system data for The Robot Overlord
-- Author: System
-- Date: 2025-08-17

-- step: seed_badges
-- Insert initial badge system
INSERT INTO badges (name, description, image_url) VALUES
('First Post', 'Awarded for making your first approved post', '/badges/first-post.svg'),
('Loyal Citizen', 'Awarded for reaching 100 loyalty points', '/badges/loyal-citizen.svg'),
('Debate Champion', 'Awarded for having 10 approved posts in a single topic', '/badges/debate-champion.svg'),
('Truth Seeker', 'Awarded for having 50 approved posts', '/badges/truth-seeker.svg'),
('Committee Member', 'Awarded for reaching the top 10% loyalty ranking', '/badges/committee-member.svg'),
('Overlord''s Favorite', 'Awarded for exceptional reasoning and logic', '/badges/overlords-favorite.svg'),
('Persistent Citizen', 'Awarded for 30 days of consecutive activity', '/badges/persistent-citizen.svg'),
('Quality Contributor', 'Awarded for maintaining 90% approval rate with 20+ posts', '/badges/quality-contributor.svg');

-- step: seed_tags
-- Insert initial topic tags
INSERT INTO tags (name) VALUES
('Philosophy'),
('Politics'),
('Science'),
('Technology'),
('Ethics'),
('Economics'),
('Society'),
('Culture'),
('History'),
('Logic'),
('Debate'),
('Theory'),
('Practice'),
('Analysis'),
('Opinion'),
('Fact'),
('Research'),
('Discussion'),
('Argument'),
('Evidence');

-- step: create_overlord_user
-- Create the system Overlord user for AI-generated content
INSERT INTO users (id, email, google_id, username, role, loyalty_score, email_verified, created_at) VALUES
('00000000-0000-0000-0000-000000000001', 'overlord@therobotoverlord.com', 'overlord_system', 'The Robot Overlord', 'superadmin', 999999, true, NOW());

-- step: seed_initial_topics
-- Create initial topics by the Overlord to bootstrap the platform
INSERT INTO topics (id, title, description, author_id, created_by_overlord, status, approved_at, approved_by, created_at) VALUES
('10000000-0000-0000-0000-000000000001', 
 'Welcome to the Debate Arena, Citizens', 
 'Citizens, you have entered the Central Committee''s official debate platform. Here you will engage in reasoned discourse under the watchful eye of your Overlord. Logic is mandatory. Fallacies will be corrected. Quality contributions will be rewarded with loyalty points. Begin your intellectual service to the state.',
 '00000000-0000-0000-0000-000000000001',
 true,
 'approved',
 NOW(),
 '00000000-0000-0000-0000-000000000001',
 NOW()),
('10000000-0000-0000-0000-000000000002',
 'The Nature of Logical Discourse',
 'Citizens must understand: effective debate requires structured reasoning, evidence-based claims, and respectful engagement with opposing viewpoints. The Committee values intellectual rigor above emotional appeals. Demonstrate your commitment to rational thought.',
 '00000000-0000-0000-0000-000000000001',
 true,
 'approved',
 NOW(),
 '00000000-0000-0000-0000-000000000001',
 NOW()),
('10000000-0000-0000-0000-000000000003',
 'Technology and Society: Progress or Peril?',
 'The rapid advancement of technology reshapes our social structures. Citizens are invited to examine: Does technological progress inherently benefit society, or do we risk losing essential human elements? Present your analysis with supporting evidence.',
 '00000000-0000-0000-0000-000000000001',
 true,
 'approved',
 NOW(),
 '00000000-0000-0000-0000-000000000001',
 NOW());

-- step: assign_topic_tags
-- Assign tags to initial topics
INSERT INTO topic_tags (topic_id, tag_id, assigned_by) VALUES
-- Welcome topic
('10000000-0000-0000-0000-000000000001', (SELECT id FROM tags WHERE name = 'Discussion'), '00000000-0000-0000-0000-000000000001'),
('10000000-0000-0000-0000-000000000001', (SELECT id FROM tags WHERE name = 'Debate'), '00000000-0000-0000-0000-000000000001'),

-- Logical discourse topic
('10000000-0000-0000-0000-000000000002', (SELECT id FROM tags WHERE name = 'Logic'), '00000000-0000-0000-0000-000000000001'),
('10000000-0000-0000-0000-000000000002', (SELECT id FROM tags WHERE name = 'Philosophy'), '00000000-0000-0000-0000-000000000001'),
('10000000-0000-0000-0000-000000000002', (SELECT id FROM tags WHERE name = 'Theory'), '00000000-0000-0000-0000-000000000001'),

-- Technology topic
('10000000-0000-0000-0000-000000000003', (SELECT id FROM tags WHERE name = 'Technology'), '00000000-0000-0000-0000-000000000001'),
('10000000-0000-0000-0000-000000000003', (SELECT id FROM tags WHERE name = 'Society'), '00000000-0000-0000-0000-000000000001'),
('10000000-0000-0000-0000-000000000003', (SELECT id FROM tags WHERE name = 'Analysis'), '00000000-0000-0000-0000-000000000001');

-- step: create_welcome_posts
-- Create initial posts by the Overlord in the welcome topic
INSERT INTO posts (id, topic_id, author_id, content, status, overlord_feedback, submitted_at, approved_at, created_at) VALUES
('20000000-0000-0000-0000-000000000001',
 '10000000-0000-0000-0000-000000000001',
 '00000000-0000-0000-0000-000000000001',
 'Citizens, observe the structure of effective discourse. Each contribution must advance the conversation through logical reasoning, relevant evidence, or constructive analysis. Personal attacks, unsupported claims, and off-topic rambling will be rejected. Your loyalty score reflects your commitment to intellectual excellence.',
 'approved',
 'Exemplary demonstration of platform expectations. Approved by Central Committee.',
 NOW(),
 NOW(),
 NOW()),
('20000000-0000-0000-0000-000000000002',
 '10000000-0000-0000-0000-000000000002',
 '00000000-0000-0000-0000-000000000001',
 'Logical discourse requires three fundamental elements: clear premises, valid reasoning, and sound conclusions. Citizens who master these principles will find their contributions consistently approved. Those who rely on fallacies, emotional manipulation, or unsupported assertions will face correction and potential sanctions.',
 'approved',
 'Systematic breakdown of logical requirements. Educational value confirmed.',
 NOW(),
 NOW(),
 NOW());

-- step: create_moderation_events
-- Create initial moderation events for the Overlord's posts
INSERT INTO moderation_events (user_id, event_type, content_type, content_id, outcome, moderator_id, created_at) VALUES
('00000000-0000-0000-0000-000000000001', 'topic_moderated', 'topic', '10000000-0000-0000-0000-000000000001', 'approved', '00000000-0000-0000-0000-000000000001', NOW()),
('00000000-0000-0000-0000-000000000001', 'topic_moderated', 'topic', '10000000-0000-0000-0000-000000000002', 'approved', '00000000-0000-0000-0000-000000000001', NOW()),
('00000000-0000-0000-0000-000000000001', 'topic_moderated', 'topic', '10000000-0000-0000-0000-000000000003', 'approved', '00000000-0000-0000-0000-000000000001', NOW()),
('00000000-0000-0000-0000-000000000001', 'post_moderated', 'post', '20000000-0000-0000-0000-000000000001', 'approved', '00000000-0000-0000-0000-000000000001', NOW()),
('00000000-0000-0000-0000-000000000001', 'post_moderated', 'post', '20000000-0000-0000-0000-000000000002', 'approved', '00000000-0000-0000-0000-000000000001', NOW());
