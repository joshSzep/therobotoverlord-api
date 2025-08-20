-- Migration: 011_add_rbac_system.sql
-- Description: Add Role-Based Access Control (RBAC) system tables
-- Author: System
-- Date: 2025-08-20

-- step: create_roles_table
-- Roles table for defining system roles
CREATE TABLE roles (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- step: create_permissions_table
-- Permissions table for defining system permissions
CREATE TABLE permissions (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_dynamic BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- step: create_role_permissions_table
-- Junction table for role-permission relationships
CREATE TABLE role_permissions (
    role_pk UUID NOT NULL REFERENCES roles(pk) ON DELETE CASCADE,
    permission_pk UUID NOT NULL REFERENCES permissions(pk) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (role_pk, permission_pk)
);

-- step: create_user_roles_table
-- Junction table for user-role relationships
CREATE TABLE user_roles (
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    role_pk UUID NOT NULL REFERENCES roles(pk) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by_pk UUID REFERENCES users(pk),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (user_pk, role_pk)
);

-- step: create_user_permissions_table
-- Direct user permissions (overrides and dynamic permissions)
CREATE TABLE user_permissions (
    user_pk UUID NOT NULL REFERENCES users(pk) ON DELETE CASCADE,
    permission_pk UUID NOT NULL REFERENCES permissions(pk) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    granted_by_event VARCHAR(50),
    granted_by_user_pk UUID REFERENCES users(pk),
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (user_pk, permission_pk)
);

-- step: create_rbac_indexes
-- Indexes for RBAC tables
CREATE INDEX idx_roles_name ON roles(name);
CREATE INDEX idx_permissions_name ON permissions(name);
CREATE INDEX idx_permissions_dynamic ON permissions(is_dynamic);
CREATE INDEX idx_role_permissions_role ON role_permissions(role_pk);
CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_pk);
CREATE INDEX idx_user_roles_user ON user_roles(user_pk);
CREATE INDEX idx_user_roles_role ON user_roles(role_pk);
CREATE INDEX idx_user_roles_active ON user_roles(user_pk, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_user_permissions_user ON user_permissions(user_pk);
CREATE INDEX idx_user_permissions_permission ON user_permissions(permission_pk);
CREATE INDEX idx_user_permissions_active ON user_permissions(user_pk, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_user_permissions_expires ON user_permissions(expires_at) WHERE expires_at IS NOT NULL;

-- step: seed_default_roles
-- Seed default roles
INSERT INTO roles (name, description) VALUES
    ('super_admin', 'Super Administrator with full system access'),
    ('admin', 'Administrator with elevated privileges'),
    ('moderator', 'Content moderator with moderation capabilities'),
    ('citizen', 'Regular platform user'),
    ('anonymous', 'Anonymous visitor (read-only access)');

-- step: seed_default_permissions
-- Seed default permissions
INSERT INTO permissions (name, description, is_dynamic) VALUES
    -- Content permissions
    ('posts.create', 'Create new posts', FALSE),
    ('posts.edit_own', 'Edit own posts', FALSE),
    ('posts.edit_any', 'Edit any post', FALSE),
    ('posts.delete_own', 'Delete own posts', FALSE),
    ('posts.delete_any', 'Delete any post', FALSE),
    ('posts.view_rejected', 'View rejected posts', FALSE),

    -- Topic permissions
    ('topics.create', 'Create new topics', FALSE),
    ('topics.edit_own', 'Edit own topics', FALSE),
    ('topics.edit_any', 'Edit any topic', FALSE),
    ('topics.delete_own', 'Delete own topics', FALSE),
    ('topics.delete_any', 'Delete any topic', FALSE),
    ('topics.approve', 'Approve pending topics', FALSE),

    -- Moderation permissions
    ('moderation.review_posts', 'Review posts in moderation queue', FALSE),
    ('moderation.review_topics', 'Review topics in moderation queue', FALSE),
    ('moderation.review_appeals', 'Review user appeals', FALSE),
    ('moderation.apply_sanctions', 'Apply sanctions to users', FALSE),
    ('moderation.remove_sanctions', 'Remove sanctions from users', FALSE),

    -- User management permissions
    ('users.view_profiles', 'View user profiles', FALSE),
    ('users.edit_own_profile', 'Edit own profile', FALSE),
    ('users.edit_any_profile', 'Edit any user profile', FALSE),
    ('users.ban_users', 'Ban users from platform', FALSE),
    ('users.unban_users', 'Unban users from platform', FALSE),
    ('users.assign_roles', 'Assign roles to users', FALSE),

    -- Administrative permissions
    ('admin.view_dashboard', 'Access admin dashboard', FALSE),
    ('admin.manage_system', 'Manage system settings', FALSE),
    ('admin.view_analytics', 'View platform analytics', FALSE),
    ('admin.manage_badges', 'Create and manage badges', FALSE),
    ('admin.manage_tags', 'Create and manage tags', FALSE),

    -- Dynamic permissions (loyalty-based)
    ('posts.create_multiple', 'Create multiple posts per day', TRUE),
    ('posts.create_premium', 'Create premium content posts', TRUE),
    ('topics.create_featured', 'Create featured topics', TRUE),
    ('appeals.priority_review', 'Get priority appeal reviews', TRUE),
    ('leaderboard.featured', 'Appear on featured leaderboard', TRUE);

-- step: assign_role_permissions
-- Assign permissions to roles
WITH role_permission_assignments AS (
    SELECT
        r.pk as role_pk,
        p.pk as permission_pk
    FROM roles r
    CROSS JOIN permissions p
    WHERE
        -- Super Admin gets all permissions
        (r.name = 'super_admin') OR

        -- Admin permissions
        (r.name = 'admin' AND p.name IN (
            'posts.create', 'posts.edit_own', 'posts.delete_own', 'posts.view_rejected',
            'topics.create', 'topics.edit_own', 'topics.delete_own', 'topics.approve',
            'moderation.review_posts', 'moderation.review_topics', 'moderation.review_appeals',
            'moderation.apply_sanctions', 'moderation.remove_sanctions',
            'users.view_profiles', 'users.edit_own_profile', 'users.edit_any_profile',
            'users.ban_users', 'users.unban_users', 'users.assign_roles',
            'admin.view_dashboard', 'admin.manage_system', 'admin.view_analytics',
            'admin.manage_badges', 'admin.manage_tags'
        )) OR

        -- Moderator permissions
        (r.name = 'moderator' AND p.name IN (
            'posts.create', 'posts.edit_own', 'posts.delete_own', 'posts.view_rejected',
            'topics.create', 'topics.edit_own', 'topics.delete_own',
            'moderation.review_posts', 'moderation.review_topics', 'moderation.review_appeals',
            'moderation.apply_sanctions',
            'users.view_profiles', 'users.edit_own_profile'
        )) OR

        -- Citizen permissions
        (r.name = 'citizen' AND p.name IN (
            'posts.create', 'posts.edit_own', 'posts.delete_own',
            'topics.create', 'topics.edit_own', 'topics.delete_own',
            'users.view_profiles', 'users.edit_own_profile'
        )) OR

        -- Anonymous permissions (read-only)
        (r.name = 'anonymous' AND p.name IN (
            'users.view_profiles'
        ))
)
INSERT INTO role_permissions (role_pk, permission_pk)
SELECT role_pk, permission_pk FROM role_permission_assignments;

-- step: assign_default_user_roles
-- Assign default citizen role to existing users (excluding Overlord)
INSERT INTO user_roles (user_pk, role_pk, assigned_by_pk)
SELECT
    u.pk as user_pk,
    r.pk as role_pk,
    NULL as assigned_by_pk
FROM users u
CROSS JOIN roles r
WHERE r.name = 'citizen'
AND u.email != 'overlord@therobotoverlord.com';

-- step: assign_overlord_super_admin
-- Assign super_admin role to Overlord user
INSERT INTO user_roles (user_pk, role_pk, assigned_by_pk)
SELECT
    u.pk as user_pk,
    r.pk as role_pk,
    u.pk as assigned_by_pk
FROM users u
CROSS JOIN roles r
WHERE r.name = 'super_admin'
AND u.email = 'overlord@therobotoverlord.com';

-- step: create_permission_resolution_function
-- Function to resolve user permissions (combines role and direct permissions)
CREATE OR REPLACE FUNCTION get_user_permissions(target_user_pk UUID)
RETURNS TABLE(permission_name VARCHAR(100), is_dynamic BOOLEAN, expires_at TIMESTAMP WITH TIME ZONE)
LANGUAGE SQL
STABLE
AS $$
    -- Get permissions from roles
    SELECT DISTINCT
        p.name as permission_name,
        p.is_dynamic,
        ur.expires_at
    FROM user_roles ur
    JOIN role_permissions rp ON ur.role_pk = rp.role_pk
    JOIN permissions p ON rp.permission_pk = p.pk
    WHERE ur.user_pk = target_user_pk
    AND ur.is_active = TRUE
    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())

    UNION

    -- Get direct user permissions
    SELECT DISTINCT
        p.name as permission_name,
        p.is_dynamic,
        up.expires_at
    FROM user_permissions up
    JOIN permissions p ON up.permission_pk = p.pk
    WHERE up.user_pk = target_user_pk
    AND up.is_active = TRUE
    AND (up.expires_at IS NULL OR up.expires_at > NOW());
$$;

-- step: create_rbac_triggers
-- Trigger to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_permissions_updated_at
    BEFORE UPDATE ON permissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
