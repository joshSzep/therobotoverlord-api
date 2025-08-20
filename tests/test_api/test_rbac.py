"""Tests for RBAC API endpoints."""

from datetime import UTC
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import HTTPException

from therobotoverlord_api.api.rbac import assign_role_to_user
from therobotoverlord_api.api.rbac import check_multiple_permissions
from therobotoverlord_api.api.rbac import check_user_permission
from therobotoverlord_api.api.rbac import cleanup_expired_permissions
from therobotoverlord_api.api.rbac import create_permission
from therobotoverlord_api.api.rbac import create_role
from therobotoverlord_api.api.rbac import get_dynamic_permissions
from therobotoverlord_api.api.rbac import get_permission
from therobotoverlord_api.api.rbac import get_permissions
from therobotoverlord_api.api.rbac import get_role
from therobotoverlord_api.api.rbac import get_roles
from therobotoverlord_api.api.rbac import get_user_admin_status
from therobotoverlord_api.api.rbac import get_user_roles
from therobotoverlord_api.api.rbac import require_admin_permission
from therobotoverlord_api.api.rbac import require_moderator_permission
from therobotoverlord_api.api.rbac import update_loyalty_permissions
from therobotoverlord_api.database.models.rbac import Permission
from therobotoverlord_api.database.models.rbac import PermissionCheckResult
from therobotoverlord_api.database.models.rbac import PermissionCreate
from therobotoverlord_api.database.models.rbac import Role
from therobotoverlord_api.database.models.rbac import RoleCreate
from therobotoverlord_api.database.models.rbac import RoleWithPermissions
from therobotoverlord_api.database.models.rbac import UserWithRoles
from therobotoverlord_api.database.models.user import User


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        pk=uuid4(),
        google_id="test_google_id",
        email="test@example.com",
        username="testuser",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_role():
    """Sample role for testing."""
    return Role(
        pk=uuid4(),
        name="test_role",
        description="Test role description",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_permission():
    """Sample permission for testing."""
    return Permission(
        pk=uuid4(),
        name="test.permission",
        description="Test permission",
        is_dynamic=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestRBACDependencies:
    """Test RBAC dependency functions."""

    @pytest.mark.asyncio
    async def test_require_admin_permission_success(self, sample_user):
        """Test require_admin_permission with admin user."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.is_user_admin = AsyncMock(return_value=True)

            result = await require_admin_permission(sample_user)

            assert result == sample_user
            mock_service.is_user_admin.assert_called_once_with(sample_user.pk)

    @pytest.mark.asyncio
    async def test_require_admin_permission_forbidden(self, sample_user):
        """Test require_admin_permission with non-admin user."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.is_user_admin = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await require_admin_permission(sample_user)

            exc = cast("HTTPException", exc_info.value)
            assert exc.status_code == 403
            assert "Admin permissions required" in str(exc.detail)

    @pytest.mark.asyncio
    async def test_require_moderator_permission_success(self, sample_user):
        """Test require_moderator_permission with moderator user."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.is_user_moderator = AsyncMock(return_value=True)

            result = await require_moderator_permission(sample_user)

            assert result == sample_user
            mock_service.is_user_moderator.assert_called_once_with(sample_user.pk)

    @pytest.mark.asyncio
    async def test_require_moderator_permission_forbidden(self, sample_user):
        """Test require_moderator_permission with non-moderator user."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.is_user_moderator = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await require_moderator_permission(sample_user)

            exc = cast("HTTPException", exc_info.value)
            assert exc.status_code == 403
            assert "Moderator permissions required" in str(exc.detail)


class TestRoleEndpoints:
    """Test role management endpoints."""

    @pytest.mark.asyncio
    async def test_get_roles(self, sample_role, sample_user):
        """Test GET /roles endpoint."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.get_all_roles = AsyncMock(return_value=[sample_role])

            result = await get_roles(current_user=sample_user)

            assert result == [sample_role]
            mock_service.get_all_roles.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_role(self, sample_role, sample_user):
        """Test POST /roles endpoint."""
        role_data = RoleCreate(name="new_role", description="New role")

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.create_role = AsyncMock(return_value=sample_role)

            result = await create_role(role_data, current_user=sample_user)

            assert result == sample_role
            mock_service.create_role.assert_called_once_with(role_data)

    @pytest.mark.asyncio
    async def test_get_role_success(self, sample_role, sample_user):
        """Test GET /roles/{role_id} endpoint success."""
        role_id = uuid4()
        role_with_permissions = RoleWithPermissions(
            pk=role_id,
            name="test_role",
            description="Test role",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            permissions=[],
        )

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.get_role_with_permissions = AsyncMock(
                return_value=role_with_permissions
            )

            result = await get_role(role_id, current_user=sample_user)

            assert result == role_with_permissions
            mock_service.get_role_with_permissions.assert_called_once_with(role_id)

    @pytest.mark.asyncio
    async def test_get_role_not_found(self, sample_user):
        """Test GET /roles/{role_id} endpoint not found."""
        role_id = uuid4()

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.get_role_with_permissions = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_role(role_id, current_user=sample_user)

            exc = cast("HTTPException", exc_info.value)
            assert exc.status_code == 404
            assert "Role not found" in str(exc.detail)


class TestPermissionEndpoints:
    """Test permission management endpoints."""

    @pytest.mark.asyncio
    async def test_get_permissions(self, sample_permission, sample_user):
        """Test GET /permissions endpoint."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.get_all_permissions = AsyncMock(
                return_value=[sample_permission]
            )

            result = await get_permissions(current_user=sample_user)

            assert result == [sample_permission]
            mock_service.get_all_permissions.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_permission(self, sample_permission, sample_user):
        """Test POST /permissions endpoint."""
        permission_data = PermissionCreate(
            name="new.permission", description="New permission"
        )

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.create_permission = AsyncMock(return_value=sample_permission)

            result = await create_permission(permission_data, current_user=sample_user)

            assert result == sample_permission
            mock_service.create_permission.assert_called_once_with(permission_data)


class TestUserRoleEndpoints:
    """Test user role management endpoints."""

    @pytest.mark.asyncio
    async def test_get_user_roles_own(self, sample_user):
        """Test GET /users/{user_id}/roles for own user."""
        user_with_roles = UserWithRoles(
            user_pk=sample_user.pk, roles=[], permissions=[]
        )

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.get_user_with_roles = AsyncMock(return_value=user_with_roles)

            result = await get_user_roles(sample_user.pk, sample_user)

            assert result == user_with_roles
            mock_service.get_user_with_roles.assert_called_once_with(sample_user.pk)

    @pytest.mark.asyncio
    async def test_get_user_roles_other_as_moderator(self, sample_user):
        """Test GET /users/{user_id}/roles for other user as moderator."""
        other_user_pk = uuid4()
        user_with_roles = UserWithRoles(user_pk=other_user_pk, roles=[], permissions=[])

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.is_user_moderator = AsyncMock(return_value=True)
            mock_service.get_user_with_roles = AsyncMock(return_value=user_with_roles)

            result = await get_user_roles(other_user_pk, sample_user)

            assert result == user_with_roles
            mock_service.is_user_moderator.assert_called_once_with(sample_user.pk)
            mock_service.get_user_with_roles.assert_called_once_with(other_user_pk)

    @pytest.mark.asyncio
    async def test_get_user_roles_other_forbidden(self, sample_user):
        """Test GET /users/{user_id}/roles for other user without permission."""
        other_user_pk = uuid4()

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.is_user_moderator = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await get_user_roles(other_user_pk, sample_user)

            exc = cast("HTTPException", exc_info.value)
            assert exc.status_code == 403
            assert "Cannot view other users' roles" in str(exc.detail)

    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, sample_user):
        """Test POST /users/{user_id}/roles/{role_id} endpoint."""
        user_id = uuid4()
        role_id = uuid4()

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.assign_role_to_user = AsyncMock(return_value=True)

            result = await assign_role_to_user(user_id, role_id, sample_user)

            expected_result = {"message": "Role assigned to user successfully"}
            assert result == expected_result
            mock_service.assign_role_to_user.assert_called_once_with(
                user_id, role_id, assigned_by_pk=sample_user.pk
            )


class TestPermissionCheckingEndpoints:
    """Test permission checking endpoints."""

    @pytest.mark.asyncio
    async def test_check_user_permission_own(self, sample_user):
        """Test GET /users/{user_id}/permissions/{permission_name}/check for own user."""
        permission_name = "test.permission"
        check_result = PermissionCheckResult(has_permission=True, source="role")

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.has_permission = AsyncMock(return_value=check_result)

            result = await check_user_permission(
                sample_user.pk, permission_name, sample_user
            )

            assert result == check_result
            mock_service.has_permission.assert_called_once_with(
                sample_user.pk, permission_name
            )

    @pytest.mark.asyncio
    async def test_check_multiple_permissions(self, sample_user):
        """Test POST /users/{user_id}/permissions/check endpoint."""
        permission_names = ["perm1", "perm2"]
        check_results = {
            "perm1": PermissionCheckResult(has_permission=True),
            "perm2": PermissionCheckResult(has_permission=False),
        }

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.check_multiple_permissions = AsyncMock(
                return_value=check_results
            )

            result = await check_multiple_permissions(
                sample_user.pk, permission_names, sample_user
            )

            assert result == check_results
            mock_service.check_multiple_permissions.assert_called_once_with(
                sample_user.pk, permission_names
            )


class TestUtilityEndpoints:
    """Test utility endpoints."""

    @pytest.mark.asyncio
    async def test_get_dynamic_permissions(self, sample_permission, sample_user):
        """Test GET /permissions/dynamic endpoint."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.get_dynamic_permissions = AsyncMock(
                return_value=[sample_permission]
            )

            result = await get_dynamic_permissions(current_user=sample_user)

            assert result == [sample_permission]
            mock_service.get_dynamic_permissions.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_permissions(self, sample_user):
        """Test POST /maintenance/cleanup-expired endpoint."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.cleanup_expired_permissions = AsyncMock(return_value=5)

            result = await cleanup_expired_permissions(current_user=sample_user)

            expected_result = {"message": "Cleaned up 5 expired permissions"}
            assert result == expected_result
            mock_service.cleanup_expired_permissions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_admin_status_own(self, sample_user):
        """Test GET /users/{user_id}/admin-status for own user."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.is_user_admin = AsyncMock(return_value=True)
            mock_service.is_user_moderator = AsyncMock(return_value=True)

            result = await get_user_admin_status(sample_user.pk, sample_user)

            expected_result = {"is_admin": True, "is_moderator": True}
            assert result == expected_result
            mock_service.is_user_admin.assert_called_once_with(sample_user.pk)
            mock_service.is_user_moderator.assert_called_once_with(sample_user.pk)

    @pytest.mark.asyncio
    async def test_update_loyalty_permissions(self, sample_user):
        """Test POST /users/{user_id}/permissions/loyalty-update endpoint."""
        user_id = uuid4()
        loyalty_score = 1000

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.grant_dynamic_permission_by_loyalty = AsyncMock(
                return_value=["perm1"]
            )
            mock_service.revoke_dynamic_permissions_below_threshold = AsyncMock(
                return_value=["perm2"]
            )

            result = await update_loyalty_permissions(
                user_id, loyalty_score, sample_user
            )

            expected_result = {
                "message": "Loyalty permissions updated successfully",
                "granted_permissions": ["perm1"],
                "revoked_permissions": ["perm2"],
            }
            assert result == expected_result
            mock_service.grant_dynamic_permission_by_loyalty.assert_called_once_with(
                user_id, loyalty_score
            )
            mock_service.revoke_dynamic_permissions_below_threshold.assert_called_once_with(
                user_id, loyalty_score
            )


class TestErrorHandling:
    """Test error handling in endpoints."""

    @pytest.mark.asyncio
    async def test_get_permission_not_found(self, sample_user):
        """Test GET /permissions/{permission_id} not found."""
        permission_id = uuid4()

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.get_permission = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_permission(permission_id, current_user=sample_user)

            exc = cast("HTTPException", exc_info.value)
            assert exc.status_code == 404
            assert "Permission not found" in str(exc.detail)

    @pytest.mark.asyncio
    async def test_assign_role_to_user_failure(self, sample_user):
        """Test POST /users/{user_id}/roles/{role_id} failure."""
        user_id = uuid4()
        role_id = uuid4()

        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.assign_role_to_user = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await assign_role_to_user(user_id, role_id, sample_user)

            exc = cast("HTTPException", exc_info.value)
            assert exc.status_code == 400
            assert "Failed to assign role to user" in str(exc.detail)

    @pytest.mark.asyncio
    async def test_get_user_roles_not_found(self, sample_user):
        """Test GET /users/{user_id}/roles when user not found."""
        with patch("therobotoverlord_api.api.rbac.rbac_service") as mock_service:
            mock_service.get_user_with_roles = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_user_roles(sample_user.pk, sample_user)

            exc = cast("HTTPException", exc_info.value)
            assert exc.status_code == 404
            assert "User not found" in str(exc.detail)
