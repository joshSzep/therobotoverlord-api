"""RBAC API endpoints for The Robot Overlord API."""

from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from therobotoverlord_api.api.auth import get_current_user
from therobotoverlord_api.database.models.rbac import Permission
from therobotoverlord_api.database.models.rbac import PermissionCheckResult
from therobotoverlord_api.database.models.rbac import PermissionCreate
from therobotoverlord_api.database.models.rbac import PermissionUpdate
from therobotoverlord_api.database.models.rbac import Role
from therobotoverlord_api.database.models.rbac import RoleCreate
from therobotoverlord_api.database.models.rbac import RoleUpdate
from therobotoverlord_api.database.models.rbac import RoleWithPermissions
from therobotoverlord_api.database.models.rbac import UserPermissionSummary
from therobotoverlord_api.database.models.rbac import UserWithRoles
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.rbac_service import RBACService

router = APIRouter(prefix="/api/v1/rbac", tags=["rbac"])
rbac_service = RBACService()


async def require_admin_permission(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to require admin permissions."""
    is_admin = await rbac_service.is_user_admin(current_user.pk)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required"
        )
    return current_user


async def require_moderator_permission(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to require moderator permissions."""
    is_moderator = await rbac_service.is_user_moderator(current_user.pk)
    if not is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator permissions required",
        )
    return current_user


# Role Management Endpoints
@router.get("/roles", response_model=list[Role])
async def get_roles(current_user: User = Depends(require_moderator_permission)):
    """Get all roles."""
    return await rbac_service.get_all_roles()


@router.post("/roles", response_model=Role, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate, current_user: User = Depends(require_admin_permission)
):
    """Create a new role."""
    return await rbac_service.create_role(role_data)


@router.get("/roles/{role_id}", response_model=RoleWithPermissions)
async def get_role(
    role_id: UUID, current_user: User = Depends(require_moderator_permission)
):
    """Get role with permissions."""
    role = await rbac_service.get_role_with_permissions(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    return role


@router.put("/roles/{role_id}", response_model=Role)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    current_user: User = Depends(require_admin_permission),
):
    """Update a role."""
    role = await rbac_service.update_role(role_id, role_data)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    return role


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID, current_user: User = Depends(require_admin_permission)
):
    """Delete a role."""
    success = await rbac_service.delete_role(role_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )


# Permission Management Endpoints
@router.get("/permissions", response_model=list[Permission])
async def get_permissions(current_user: User = Depends(require_moderator_permission)):
    """Get all permissions."""
    return await rbac_service.get_all_permissions()


@router.post(
    "/permissions", response_model=Permission, status_code=status.HTTP_201_CREATED
)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: User = Depends(require_admin_permission),
):
    """Create a new permission."""
    return await rbac_service.create_permission(permission_data)


@router.get("/permissions/{permission_id}", response_model=Permission)
async def get_permission(
    permission_id: UUID, current_user: User = Depends(require_moderator_permission)
):
    """Get permission by ID."""
    permission = await rbac_service.get_permission(permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )
    return permission


@router.put("/permissions/{permission_id}", response_model=Permission)
async def update_permission(
    permission_id: UUID,
    permission_data: PermissionUpdate,
    current_user: User = Depends(require_admin_permission),
):
    """Update a permission."""
    permission = await rbac_service.update_permission(permission_id, permission_data)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )
    return permission


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: UUID, current_user: User = Depends(require_admin_permission)
):
    """Delete a permission."""
    success = await rbac_service.delete_permission(permission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )


# Role-Permission Management
@router.post(
    "/roles/{role_id}/permissions/{permission_id}", status_code=status.HTTP_201_CREATED
)
async def assign_permission_to_role(
    role_id: UUID,
    permission_id: UUID,
    current_user: User = Depends(require_admin_permission),
):
    """Assign a permission to a role."""
    success = await rbac_service.assign_permission_to_role(role_id, permission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign permission to role",
        )
    return {"message": "Permission assigned to role successfully"}


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    current_user: User = Depends(require_admin_permission),
):
    """Remove a permission from a role."""
    success = await rbac_service.remove_permission_from_role(role_id, permission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not assigned to role",
        )


@router.get("/roles/{role_id}/permissions", response_model=list[Permission])
async def get_role_permissions(
    role_id: UUID, current_user: User = Depends(require_moderator_permission)
):
    """Get all permissions for a role."""
    return await rbac_service.get_role_permissions(role_id)


# User Role Management
@router.get("/users/{user_id}/roles", response_model=UserWithRoles)
async def get_user_roles(user_id: UUID, current_user: User = Depends(get_current_user)):
    """Get user's roles and permissions."""
    # Users can view their own roles, moderators can view any user's roles
    if user_id != current_user.pk:
        is_moderator = await rbac_service.is_user_moderator(current_user.pk)
        if not is_moderator:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view other users' roles",
            )

    user_roles = await rbac_service.get_user_with_roles(user_id)
    if not user_roles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user_roles


@router.post("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    user_id: UUID, role_id: UUID, current_user: User = Depends(require_admin_permission)
):
    """Assign a role to a user."""
    success = await rbac_service.assign_role_to_user(
        user_id, role_id, assigned_by_pk=current_user.pk
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign role to user",
        )
    return {"message": "Role assigned to user successfully"}


@router.delete(
    "/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_role_from_user(
    user_id: UUID, role_id: UUID, current_user: User = Depends(require_admin_permission)
):
    """Remove a role from a user."""
    success = await rbac_service.remove_role_from_user(user_id, role_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not assigned to user"
        )


# User Permission Management
@router.get("/users/{user_id}/permissions", response_model=list[UserPermissionSummary])
async def get_user_permissions(
    user_id: UUID, current_user: User = Depends(get_current_user)
):
    """Get user's permissions summary."""
    # Users can view their own permissions, moderators can view any user's permissions
    if user_id != current_user.pk:
        is_moderator = await rbac_service.is_user_moderator(current_user.pk)
        if not is_moderator:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view other users' permissions",
            )

    return await rbac_service.get_user_permissions(user_id)


@router.post(
    "/users/{user_id}/permissions/{permission_id}", status_code=status.HTTP_201_CREATED
)
async def grant_permission_to_user(
    user_id: UUID,
    permission_id: UUID,
    current_user: User = Depends(require_admin_permission),
):
    """Grant a direct permission to a user."""
    success = await rbac_service.grant_permission_to_user(
        user_id, permission_id, granted_by_user_pk=current_user.pk
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to grant permission to user",
        )
    return {"message": "Permission granted to user successfully"}


@router.delete(
    "/users/{user_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_permission_from_user(
    user_id: UUID,
    permission_id: UUID,
    current_user: User = Depends(require_admin_permission),
):
    """Revoke a direct permission from a user."""
    success = await rbac_service.revoke_permission_from_user(user_id, permission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not granted to user",
        )


# Permission Checking
@router.get(
    "/users/{user_id}/permissions/{permission_name}/check",
    response_model=PermissionCheckResult,
)
async def check_user_permission(
    user_id: UUID, permission_name: str, current_user: User = Depends(get_current_user)
):
    """Check if user has a specific permission."""
    # Users can check their own permissions, moderators can check any user's permissions
    if user_id != current_user.pk:
        is_moderator = await rbac_service.is_user_moderator(current_user.pk)
        if not is_moderator:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot check other users' permissions",
            )

    return await rbac_service.has_permission(user_id, permission_name)


@router.post(
    "/users/{user_id}/permissions/check",
    response_model=dict[str, PermissionCheckResult],
)
async def check_multiple_permissions(
    user_id: UUID,
    permission_names: list[str],
    current_user: User = Depends(get_current_user),
):
    """Check multiple permissions for a user."""
    # Users can check their own permissions, moderators can check any user's permissions
    if user_id != current_user.pk:
        is_moderator = await rbac_service.is_user_moderator(current_user.pk)
        if not is_moderator:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot check other users' permissions",
            )

    return await rbac_service.check_multiple_permissions(user_id, permission_names)


# Dynamic Permission Management
@router.post(
    "/users/{user_id}/permissions/loyalty-update", status_code=status.HTTP_200_OK
)
async def update_loyalty_permissions(
    user_id: UUID,
    loyalty_score: int,
    current_user: User = Depends(require_admin_permission),
):
    """Update user's dynamic permissions based on loyalty score."""
    granted = await rbac_service.grant_dynamic_permission_by_loyalty(
        user_id, loyalty_score
    )
    revoked = await rbac_service.revoke_dynamic_permissions_below_threshold(
        user_id, loyalty_score
    )

    return {
        "message": "Loyalty permissions updated successfully",
        "granted_permissions": granted,
        "revoked_permissions": revoked,
    }


# Utility Endpoints
@router.get("/permissions/dynamic", response_model=list[Permission])
async def get_dynamic_permissions(
    current_user: User = Depends(require_moderator_permission),
):
    """Get all dynamic permissions."""
    return await rbac_service.get_dynamic_permissions()


@router.post("/maintenance/cleanup-expired", status_code=status.HTTP_200_OK)
async def cleanup_expired_permissions(
    current_user: User = Depends(require_admin_permission),
):
    """Clean up expired user permissions."""
    count = await rbac_service.cleanup_expired_permissions()
    return {"message": f"Cleaned up {count} expired permissions"}


@router.get("/users/{user_id}/admin-status", response_model=dict[str, bool])
async def get_user_admin_status(
    user_id: UUID, current_user: User = Depends(get_current_user)
):
    """Get user's admin/moderator status."""
    # Users can check their own status, moderators can check any user's status
    if user_id != current_user.pk:
        is_moderator = await rbac_service.is_user_moderator(current_user.pk)
        if not is_moderator:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot check other users' admin status",
            )

    is_admin = await rbac_service.is_user_admin(user_id)
    is_moderator = await rbac_service.is_user_moderator(user_id)

    return {"is_admin": is_admin, "is_moderator": is_moderator}
