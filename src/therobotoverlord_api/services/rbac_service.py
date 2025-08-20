"""RBAC service for The Robot Overlord API."""

import logging

from datetime import datetime
from uuid import UUID

from therobotoverlord_api.database.models.rbac import Permission
from therobotoverlord_api.database.models.rbac import PermissionCheckResult
from therobotoverlord_api.database.models.rbac import PermissionCreate
from therobotoverlord_api.database.models.rbac import PermissionUpdate
from therobotoverlord_api.database.models.rbac import Role
from therobotoverlord_api.database.models.rbac import RoleCreate
from therobotoverlord_api.database.models.rbac import RolePermissionCreate
from therobotoverlord_api.database.models.rbac import RoleUpdate
from therobotoverlord_api.database.models.rbac import RoleWithPermissions
from therobotoverlord_api.database.models.rbac import UserPermissionCreate
from therobotoverlord_api.database.models.rbac import UserPermissionSummary
from therobotoverlord_api.database.models.rbac import UserRoleCreate
from therobotoverlord_api.database.models.rbac import UserWithRoles
from therobotoverlord_api.database.repositories.rbac import RBACRepository

logger = logging.getLogger(__name__)


class RBACService:
    """Service for RBAC operations."""

    def __init__(self):
        self.rbac_repo = RBACRepository()

    # Role Management
    async def create_role(self, role_data: RoleCreate) -> Role:
        """Create a new role."""
        try:
            return await self.rbac_repo.roles.create_role(role_data)
        except Exception as e:
            logger.exception("Failed to create role: %s", role_data.name)
            raise

    async def get_role(self, role_pk: UUID) -> Role | None:
        """Get role by ID."""
        return await self.rbac_repo.roles.get_by_pk(role_pk)

    async def get_role_by_name(self, name: str) -> Role | None:
        """Get role by name."""
        return await self.rbac_repo.roles.get_by_name(name)

    async def get_all_roles(self) -> list[Role]:
        """Get all roles."""
        return await self.rbac_repo.roles.get_all()

    async def update_role(self, role_pk: UUID, role_data: RoleUpdate) -> Role | None:
        """Update a role."""
        try:
            return await self.rbac_repo.roles.update_role(role_pk, role_data)
        except Exception as e:
            logger.exception("Failed to update role: %s", role_pk)
            raise

    async def delete_role(self, role_pk: UUID) -> bool:
        """Delete a role."""
        try:
            return await self.rbac_repo.roles.delete_by_pk(role_pk)
        except Exception as e:
            logger.exception("Failed to delete role: %s", role_pk)
            raise

    async def get_role_with_permissions(
        self, role_pk: UUID
    ) -> RoleWithPermissions | None:
        """Get role with its permissions."""
        return await self.rbac_repo.roles.get_role_with_permissions(role_pk)

    # Permission Management
    async def create_permission(self, permission_data: PermissionCreate) -> Permission:
        """Create a new permission."""
        try:
            return await self.rbac_repo.permissions.create_permission(permission_data)
        except Exception as e:
            logger.exception("Failed to create permission: %s", permission_data.name)
            raise

    async def get_permission(self, permission_pk: UUID) -> Permission | None:
        """Get permission by ID."""
        return await self.rbac_repo.permissions.get_by_pk(permission_pk)

    async def get_permission_by_name(self, name: str) -> Permission | None:
        """Get permission by name."""
        return await self.rbac_repo.permissions.get_by_name(name)

    async def get_all_permissions(self) -> list[Permission]:
        """Get all permissions."""
        return await self.rbac_repo.permissions.get_all()

    async def get_dynamic_permissions(self) -> list[Permission]:
        """Get all dynamic permissions."""
        return await self.rbac_repo.permissions.get_dynamic_permissions()

    async def update_permission(
        self, permission_pk: UUID, permission_data: PermissionUpdate
    ) -> Permission | None:
        """Update a permission."""
        try:
            return await self.rbac_repo.permissions.update_permission(
                permission_pk, permission_data
            )
        except Exception as e:
            logger.exception("Failed to update permission: %s", permission_pk)
            raise

    async def delete_permission(self, permission_pk: UUID) -> bool:
        """Delete a permission."""
        try:
            return await self.rbac_repo.permissions.delete_by_pk(permission_pk)
        except Exception as e:
            logger.exception("Failed to delete permission: %s", permission_pk)
            raise

    # Role-Permission Management
    async def assign_permission_to_role(
        self, role_pk: UUID, permission_pk: UUID
    ) -> bool:
        """Assign a permission to a role."""
        try:
            assignment = RolePermissionCreate(
                role_pk=role_pk, permission_pk=permission_pk
            )
            await self.rbac_repo.role_permissions.assign_permission_to_role(assignment)
            return True
        except Exception as e:
            logger.exception(
                "Failed to assign permission %s to role %s", permission_pk, role_pk
            )
            raise

    async def remove_permission_from_role(
        self, role_pk: UUID, permission_pk: UUID
    ) -> bool:
        """Remove a permission from a role."""
        try:
            return await self.rbac_repo.role_permissions.remove_permission_from_role(
                role_pk, permission_pk
            )
        except Exception as e:
            logger.exception(
                "Failed to remove permission %s from role %s", permission_pk, role_pk
            )
            raise

    async def get_role_permissions(self, role_pk: UUID) -> list[Permission]:
        """Get all permissions for a role."""
        return await self.rbac_repo.role_permissions.get_role_permissions(role_pk)

    # User-Role Management
    async def assign_role_to_user(
        self,
        user_pk: UUID,
        role_pk: UUID,
        assigned_by_pk: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> bool:
        """Assign a role to a user."""
        try:
            assignment = UserRoleCreate(
                user_pk=user_pk,
                role_pk=role_pk,
                assigned_by_pk=assigned_by_pk,
                expires_at=expires_at,
            )
            await self.rbac_repo.user_roles.assign_role_to_user(assignment)
            logger.info("Assigned role %s to user %s", role_pk, user_pk)
            return True
        except Exception as e:
            logger.exception("Failed to assign role %s to user %s", role_pk, user_pk)
            raise

    async def remove_role_from_user(self, user_pk: UUID, role_pk: UUID) -> bool:
        """Remove a role from a user."""
        try:
            result = await self.rbac_repo.user_roles.remove_role_from_user(
                user_pk, role_pk
            )
            if result:
                logger.info("Removed role %s from user %s", role_pk, user_pk)
            return result
        except Exception as e:
            logger.exception("Failed to remove role %s from user %s", role_pk, user_pk)
            raise

    async def get_user_roles(self, user_pk: UUID) -> list[Role]:
        """Get all active roles for a user."""
        return await self.rbac_repo.user_roles.get_user_roles(user_pk)

    async def get_user_with_roles(self, user_pk: UUID) -> UserWithRoles | None:
        """Get user with roles and permissions."""
        return await self.rbac_repo.user_roles.get_user_with_roles(user_pk)

    # User Permission Management
    async def grant_permission_to_user(
        self,
        user_pk: UUID,
        permission_pk: UUID,
        granted_by_event: str | None = None,
        granted_by_user_pk: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> bool:
        """Grant a direct permission to a user."""
        try:
            permission_data = UserPermissionCreate(
                user_pk=user_pk,
                permission_pk=permission_pk,
                granted_by_event=granted_by_event,
                granted_by_user_pk=granted_by_user_pk,
                expires_at=expires_at,
            )
            await self.rbac_repo.user_permissions.grant_permission_to_user(
                permission_data
            )
            logger.info("Granted permission %s to user %s", permission_pk, user_pk)
            return True
        except Exception as e:
            logger.exception(
                "Failed to grant permission %s to user %s", permission_pk, user_pk
            )
            raise

    async def revoke_permission_from_user(
        self, user_pk: UUID, permission_pk: UUID
    ) -> bool:
        """Revoke a direct permission from a user."""
        try:
            result = await self.rbac_repo.user_permissions.revoke_permission_from_user(
                user_pk, permission_pk
            )
            if result:
                logger.info(
                    "Revoked permission %s from user %s", permission_pk, user_pk
                )
            return result
        except Exception as e:
            logger.exception(
                "Failed to revoke permission %s from user %s", permission_pk, user_pk
            )
            raise

    async def get_user_permissions(self, user_pk: UUID) -> list[UserPermissionSummary]:
        """Get comprehensive permission summary for a user."""
        return await self.rbac_repo.user_roles.get_user_permissions_summary(user_pk)

    # Permission Checking
    async def has_permission(
        self, user_pk: UUID, permission_name: str
    ) -> PermissionCheckResult:
        """Check if user has a specific permission."""
        try:
            has_perm = await self.rbac_repo.user_permissions.has_permission(
                user_pk, permission_name
            )

            # Get additional details if permission exists
            expires_at = None
            source = None

            if has_perm:
                permissions = await self.get_user_permissions(user_pk)
                for perm in permissions:
                    if perm.permission_name == permission_name:
                        expires_at = perm.expires_at
                        source = perm.source
                        break

            return PermissionCheckResult(
                has_permission=has_perm, expires_at=expires_at, source=source
            )
        except Exception as e:
            logger.exception(
                "Failed to check permission %s for user %s", permission_name, user_pk
            )
            raise

    async def check_multiple_permissions(
        self, user_pk: UUID, permission_names: list[str]
    ) -> dict[str, PermissionCheckResult]:
        """Check multiple permissions for a user."""
        results = {}
        for permission_name in permission_names:
            results[permission_name] = await self.has_permission(
                user_pk, permission_name
            )
        return results

    # Dynamic Permission Management
    async def grant_dynamic_permission_by_loyalty(
        self, user_pk: UUID, loyalty_score: int
    ) -> list[str]:
        """Grant dynamic permissions based on loyalty score."""
        granted_permissions = []

        try:
            # Define loyalty thresholds for dynamic permissions
            loyalty_thresholds = {
                100: ["posts.create_multiple"],
                500: ["posts.create_premium"],
                1000: ["topics.create_featured"],
                2500: ["appeals.priority_review"],
                5000: ["leaderboard.featured"],
            }

            # Get dynamic permissions that should be granted
            for threshold, permissions in loyalty_thresholds.items():
                if loyalty_score >= threshold:
                    for perm_name in permissions:
                        # Get permission by name
                        permission = await self.get_permission_by_name(perm_name)
                        if permission and permission.is_dynamic:
                            # Grant with loyalty event
                            success = await self.grant_permission_to_user(
                                user_pk=user_pk,
                                permission_pk=permission.pk,
                                granted_by_event=f"loyalty_score_{loyalty_score}",
                            )
                            if success:
                                granted_permissions.append(perm_name)

            if granted_permissions:
                logger.info(
                    "Granted dynamic permissions to user %s: %s",
                    user_pk,
                    granted_permissions,
                )

            return granted_permissions

        except Exception as e:
            logger.exception("Failed to grant dynamic permissions for user %s", user_pk)
            raise

    async def revoke_dynamic_permissions_below_threshold(
        self, user_pk: UUID, loyalty_score: int
    ) -> list[str]:
        """Revoke dynamic permissions that user no longer qualifies for."""
        revoked_permissions = []

        try:
            # Define loyalty thresholds
            loyalty_thresholds = {
                100: ["posts.create_multiple"],
                500: ["posts.create_premium"],
                1000: ["topics.create_featured"],
                2500: ["appeals.priority_review"],
                5000: ["leaderboard.featured"],
            }

            # Check which permissions should be revoked
            for threshold, permissions in loyalty_thresholds.items():
                if loyalty_score < threshold:
                    for perm_name in permissions:
                        permission = await self.get_permission_by_name(perm_name)
                        if permission:
                            success = await self.revoke_permission_from_user(
                                user_pk, permission.pk
                            )
                            if success:
                                revoked_permissions.append(perm_name)

            if revoked_permissions:
                logger.info(
                    "Revoked dynamic permissions from user %s: %s",
                    user_pk,
                    revoked_permissions,
                )

            return revoked_permissions

        except Exception as e:
            logger.exception(
                "Failed to revoke dynamic permissions for user %s", user_pk
            )
            raise

    # Maintenance Operations
    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired user permissions."""
        try:
            count = await self.rbac_repo.user_permissions.cleanup_expired_permissions()
            if count > 0:
                logger.info("Cleaned up %d expired permissions", count)
            return count
        except Exception as e:
            logger.exception("Failed to cleanup expired permissions")
            raise

    # Utility Methods
    async def get_permission_names_for_user(self, user_pk: UUID) -> list[str]:
        """Get list of permission names for a user."""
        permissions = await self.get_user_permissions(user_pk)
        return [perm.permission_name for perm in permissions]

    async def is_user_admin(self, user_pk: UUID) -> bool:
        """Check if user has admin or super_admin role."""
        roles = await self.get_user_roles(user_pk)
        admin_roles = {"admin", "super_admin"}
        return any(role.name in admin_roles for role in roles)

    async def is_user_moderator(self, user_pk: UUID) -> bool:
        """Check if user has moderator, admin, or super_admin role."""
        roles = await self.get_user_roles(user_pk)
        moderator_roles = {"moderator", "admin", "super_admin"}
        return any(role.name in moderator_roles for role in roles)

    async def assign_default_citizen_role(self, user_pk: UUID) -> bool:
        """Assign default citizen role to new user."""
        try:
            citizen_role = await self.get_role_by_name("citizen")
            if not citizen_role:
                logger.error("Citizen role not found")
                return False

            return await self.assign_role_to_user(user_pk, citizen_role.pk)
        except Exception as e:
            logger.exception(
                "Failed to assign default citizen role to user %s", user_pk
            )
            raise
