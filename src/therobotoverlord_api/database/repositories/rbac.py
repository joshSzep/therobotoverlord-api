"""RBAC repository for The Robot Overlord API."""

from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.rbac import Permission
from therobotoverlord_api.database.models.rbac import PermissionCreate
from therobotoverlord_api.database.models.rbac import PermissionUpdate
from therobotoverlord_api.database.models.rbac import Role
from therobotoverlord_api.database.models.rbac import RoleCreate
from therobotoverlord_api.database.models.rbac import RolePermission
from therobotoverlord_api.database.models.rbac import RolePermissionCreate
from therobotoverlord_api.database.models.rbac import RoleUpdate
from therobotoverlord_api.database.models.rbac import RoleWithPermissions
from therobotoverlord_api.database.models.rbac import UserPermission
from therobotoverlord_api.database.models.rbac import UserPermissionCreate
from therobotoverlord_api.database.models.rbac import UserPermissionSummary
from therobotoverlord_api.database.models.rbac import UserPermissionUpdate
from therobotoverlord_api.database.models.rbac import UserRole
from therobotoverlord_api.database.models.rbac import UserRoleCreate
from therobotoverlord_api.database.models.rbac import UserRoleUpdate
from therobotoverlord_api.database.models.rbac import UserWithRoles
from therobotoverlord_api.database.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository for role operations."""

    def __init__(self):
        super().__init__("roles")

    def _record_to_model(self, record: Record) -> Role:
        """Convert database record to Role model."""
        return Role.model_validate(record)

    async def create_role(self, role_data: RoleCreate) -> Role:
        """Create a new role."""
        data = role_data.model_dump()
        return await self.create_from_dict(data)

    async def update_role(self, role_pk: UUID, role_data: RoleUpdate) -> Role | None:
        """Update an existing role."""
        data = role_data.model_dump(exclude_unset=True)
        return await self.update_from_dict(role_pk, data)

    async def get_by_name(self, name: str) -> Role | None:
        """Get role by name."""
        return await self.find_one_by(name=name)

    async def get_role_with_permissions(
        self, role_pk: UUID
    ) -> RoleWithPermissions | None:
        """Get role with its associated permissions."""
        query = """
            SELECT
                r.pk, r.name, r.description, r.created_at, r.updated_at,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'pk', p.pk,
                            'name', p.name,
                            'description', p.description,
                            'is_dynamic', p.is_dynamic,
                            'created_at', p.created_at,
                            'updated_at', p.updated_at
                        ) ORDER BY p.name
                    ) FILTER (WHERE p.pk IS NOT NULL),
                    '[]'::json
                ) as permissions
            FROM roles r
            LEFT JOIN role_permissions rp ON r.pk = rp.role_pk
            LEFT JOIN permissions p ON rp.permission_pk = p.pk
            WHERE r.pk = $1
            GROUP BY r.pk, r.name, r.description, r.created_at, r.updated_at
        """

        async with get_db_connection() as conn:
            record = await conn.fetchrow(query, role_pk)
            if not record:
                return None

            return RoleWithPermissions.model_validate(record)


class PermissionRepository(BaseRepository[Permission]):
    """Repository for permission operations."""

    def __init__(self):
        super().__init__("permissions")

    def _record_to_model(self, record: Record) -> Permission:
        """Convert database record to Permission model."""
        return Permission.model_validate(record)

    async def create_permission(self, permission_data: PermissionCreate) -> Permission:
        """Create a new permission."""
        data = permission_data.model_dump()
        return await self.create_from_dict(data)

    async def update_permission(
        self, permission_pk: UUID, permission_data: PermissionUpdate
    ) -> Permission | None:
        """Update an existing permission."""
        data = permission_data.model_dump(exclude_unset=True)
        return await self.update_from_dict(permission_pk, data)

    async def get_by_name(self, name: str) -> Permission | None:
        """Get permission by name."""
        return await self.find_one_by(name=name)

    async def get_dynamic_permissions(self) -> list[Permission]:
        """Get all dynamic permissions."""
        return await self.find_by(is_dynamic=True)


class RolePermissionRepository:
    """Repository for role-permission junction operations."""

    async def assign_permission_to_role(
        self, assignment: RolePermissionCreate
    ) -> RolePermission:
        """Assign a permission to a role."""
        query = """
            INSERT INTO role_permissions (role_pk, permission_pk)
            VALUES ($1, $2)
            ON CONFLICT (role_pk, permission_pk) DO NOTHING
            RETURNING role_pk, permission_pk, created_at
        """

        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                query, assignment.role_pk, assignment.permission_pk
            )
            if not record:
                # Already exists, fetch it
                record = await conn.fetchrow(
                    "SELECT role_pk, permission_pk, created_at FROM role_permissions WHERE role_pk = $1 AND permission_pk = $2",
                    assignment.role_pk,
                    assignment.permission_pk,
                )

            return RolePermission.model_validate(record)

    async def remove_permission_from_role(
        self, role_pk: UUID, permission_pk: UUID
    ) -> bool:
        """Remove a permission from a role."""
        query = """
            DELETE FROM role_permissions
            WHERE role_pk = $1 AND permission_pk = $2
        """

        async with get_db_connection() as conn:
            result = await conn.execute(query, role_pk, permission_pk)
            return result != "DELETE 0"

    async def get_role_permissions(self, role_pk: UUID) -> list[Permission]:
        """Get all permissions for a role."""
        query = """
            SELECT p.pk, p.name, p.description, p.is_dynamic, p.created_at, p.updated_at
            FROM permissions p
            JOIN role_permissions rp ON p.pk = rp.permission_pk
            WHERE rp.role_pk = $1
            ORDER BY p.name
        """

        async with get_db_connection() as conn:
            records = await conn.fetch(query, role_pk)
            return [Permission.model_validate(record) for record in records]


class UserRoleRepository:
    """Repository for user-role junction operations."""

    async def assign_role_to_user(self, assignment: UserRoleCreate) -> UserRole:
        """Assign a role to a user."""
        query = """
            INSERT INTO user_roles (user_pk, role_pk, assigned_by_pk, expires_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pk, role_pk) DO UPDATE SET
                assigned_at = NOW(),
                assigned_by_pk = EXCLUDED.assigned_by_pk,
                expires_at = EXCLUDED.expires_at,
                is_active = TRUE
            RETURNING user_pk, role_pk, assigned_at, assigned_by_pk, expires_at, is_active
        """

        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                query,
                assignment.user_pk,
                assignment.role_pk,
                assignment.assigned_by_pk,
                assignment.expires_at,
            )

            return UserRole.model_validate(record)

    async def update_user_role(
        self, user_pk: UUID, role_pk: UUID, update_data: UserRoleUpdate
    ) -> UserRole | None:
        """Update a user's role assignment."""
        data = update_data.model_dump(exclude_unset=True)
        if not data:
            return None

        set_clauses = []
        values = []
        param_count = 1

        for field, value in data.items():
            set_clauses.append(f"{field} = ${param_count}")
            values.append(value)
            param_count += 1

        values.extend([user_pk, role_pk])

        query = f"""
            UPDATE user_roles
            SET {", ".join(set_clauses)}
            WHERE user_pk = ${param_count} AND role_pk = ${param_count + 1}
            RETURNING user_pk, role_pk, assigned_at, assigned_by_pk, expires_at, is_active
        """

        async with get_db_connection() as conn:
            record = await conn.fetchrow(query, *values)
            return UserRole.model_validate(record) if record else None

    async def remove_role_from_user(self, user_pk: UUID, role_pk: UUID) -> bool:
        """Remove a role from a user."""
        query = """
            UPDATE user_roles
            SET is_active = FALSE
            WHERE user_pk = $1 AND role_pk = $2
        """

        async with get_db_connection() as conn:
            result = await conn.execute(query, user_pk, role_pk)
            return result != "UPDATE 0"

    async def get_user_roles(self, user_pk: UUID) -> list[Role]:
        """Get all active roles for a user."""
        query = """
            SELECT r.pk, r.name, r.description, r.created_at, r.updated_at
            FROM roles r
            JOIN user_roles ur ON r.pk = ur.role_pk
            WHERE ur.user_pk = $1
            AND ur.is_active = TRUE
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            ORDER BY r.name
        """

        async with get_db_connection() as conn:
            records = await conn.fetch(query, user_pk)
            return [Role.model_validate(record) for record in records]

    async def get_user_with_roles(self, user_pk: UUID) -> UserWithRoles | None:
        """Get user with roles and permissions."""
        roles = await self.get_user_roles(user_pk)
        permissions = await self.get_user_permissions_summary(user_pk)

        return UserWithRoles(user_pk=user_pk, roles=roles, permissions=permissions)

    async def get_user_permissions_summary(
        self, user_pk: UUID
    ) -> list[UserPermissionSummary]:
        """Get comprehensive permission summary for a user."""
        query = """
            SELECT
                permission_name,
                is_dynamic,
                expires_at
            FROM get_user_permissions($1)
        """

        async with get_db_connection() as conn:
            records = await conn.fetch(query, user_pk)
            return [
                UserPermissionSummary(
                    permission_name=record["permission_name"],
                    is_dynamic=record["is_dynamic"],
                    expires_at=record["expires_at"],
                    source="combined",  # Function combines both sources
                )
                for record in records
            ]


class UserPermissionRepository:
    """Repository for direct user permission operations."""

    async def grant_permission_to_user(
        self, permission_data: UserPermissionCreate
    ) -> UserPermission:
        """Grant a direct permission to a user."""
        query = """
            INSERT INTO user_permissions (
                user_pk, permission_pk, expires_at, granted_by_event, granted_by_user_pk
            )
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_pk, permission_pk) DO UPDATE SET
                granted_at = NOW(),
                expires_at = EXCLUDED.expires_at,
                granted_by_event = EXCLUDED.granted_by_event,
                granted_by_user_pk = EXCLUDED.granted_by_user_pk,
                is_active = TRUE
            RETURNING user_pk, permission_pk, granted_at, expires_at, granted_by_event, granted_by_user_pk, is_active
        """

        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                query,
                permission_data.user_pk,
                permission_data.permission_pk,
                permission_data.expires_at,
                permission_data.granted_by_event,
                permission_data.granted_by_user_pk,
            )

            return UserPermission.model_validate(record)

    async def update_user_permission(
        self, user_pk: UUID, permission_pk: UUID, update_data: UserPermissionUpdate
    ) -> UserPermission | None:
        """Update a user's direct permission."""
        data = update_data.model_dump(exclude_unset=True)
        if not data:
            return None

        set_clauses = []
        values = []
        param_count = 1

        for field, value in data.items():
            set_clauses.append(f"{field} = ${param_count}")
            values.append(value)
            param_count += 1

        values.extend([user_pk, permission_pk])

        query = f"""
            UPDATE user_permissions
            SET {", ".join(set_clauses)}
            WHERE user_pk = ${param_count} AND permission_pk = ${param_count + 1}
            RETURNING user_pk, permission_pk, granted_at, expires_at, granted_by_event, granted_by_user_pk, is_active
        """

        async with get_db_connection() as conn:
            record = await conn.fetchrow(query, *values)
            return UserPermission.model_validate(record) if record else None

    async def revoke_permission_from_user(
        self, user_pk: UUID, permission_pk: UUID
    ) -> bool:
        """Revoke a direct permission from a user."""
        query = """
            UPDATE user_permissions
            SET is_active = FALSE
            WHERE user_pk = $1 AND permission_pk = $2
        """

        async with get_db_connection() as conn:
            result = await conn.execute(query, user_pk, permission_pk)
            return result != "UPDATE 0"

    async def get_user_direct_permissions(self, user_pk: UUID) -> list[UserPermission]:
        """Get all active direct permissions for a user."""
        query = """
            SELECT user_pk, permission_pk, granted_at, expires_at, granted_by_event, granted_by_user_pk, is_active
            FROM user_permissions
            WHERE user_pk = $1
            AND is_active = TRUE
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY granted_at DESC
        """

        async with get_db_connection() as conn:
            records = await conn.fetch(query, user_pk)
            return [UserPermission.model_validate(record) for record in records]

    async def has_permission(self, user_pk: UUID, permission_name: str) -> bool:
        """Check if user has a specific permission (from roles or direct)."""
        query = """
            SELECT EXISTS(
                SELECT 1 FROM get_user_permissions($1)
                WHERE permission_name = $2
            )
        """

        async with get_db_connection() as conn:
            result = await conn.fetchval(query, user_pk, permission_name)
            return bool(result)

    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired user permissions."""
        query = """
            UPDATE user_permissions
            SET is_active = FALSE
            WHERE expires_at IS NOT NULL
            AND expires_at <= NOW()
            AND is_active = TRUE
        """

        async with get_db_connection() as conn:
            result = await conn.execute(query)
            # Extract number from result like "UPDATE 5"
            return int(result.split()[-1]) if result.split()[-1].isdigit() else 0


class RBACRepository:
    """Main RBAC repository combining all RBAC operations."""

    def __init__(self):
        self.roles = RoleRepository()
        self.permissions = PermissionRepository()
        self.role_permissions = RolePermissionRepository()
        self.user_roles = UserRoleRepository()
        self.user_permissions = UserPermissionRepository()
