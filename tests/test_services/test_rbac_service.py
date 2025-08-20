"""Tests for RBAC service."""

from datetime import UTC
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest

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
from therobotoverlord_api.services.rbac_service import RBACService


@pytest.fixture
def rbac_service():
    """Create an RBACService instance for testing."""
    return RBACService()


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


@pytest.fixture
def sample_dynamic_permission():
    """Sample dynamic permission for testing."""
    return Permission(
        pk=uuid4(),
        name="posts.create_premium",
        description="Create premium posts",
        is_dynamic=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestRBACServiceRoleManagement:
    """Test role management methods."""

    @pytest.mark.asyncio
    async def test_create_role(self, rbac_service, sample_role):
        """Test creating a role."""
        role_data = RoleCreate(name="test_role", description="Test description")

        with patch.object(
            rbac_service.rbac_repo.roles, "create_role", return_value=sample_role
        ) as mock_create:
            result = await rbac_service.create_role(role_data)

            mock_create.assert_called_once_with(role_data)
            assert result == sample_role

    @pytest.mark.asyncio
    async def test_create_role_exception(self, rbac_service):
        """Test creating a role with exception."""
        role_data = RoleCreate(name="test_role")

        with patch.object(
            rbac_service.rbac_repo.roles,
            "create_role",
            side_effect=Exception("DB error"),
        ):
            with pytest.raises(Exception):
                await rbac_service.create_role(role_data)

    @pytest.mark.asyncio
    async def test_get_role(self, rbac_service, sample_role):
        """Test getting a role by ID."""
        role_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.roles, "get_by_pk", return_value=sample_role
        ) as mock_get:
            result = await rbac_service.get_role(role_pk)

            mock_get.assert_called_once_with(role_pk)
            assert result == sample_role

    @pytest.mark.asyncio
    async def test_get_role_by_name(self, rbac_service, sample_role):
        """Test getting a role by name."""
        with patch.object(
            rbac_service.rbac_repo.roles, "get_by_name", return_value=sample_role
        ) as mock_get:
            result = await rbac_service.get_role_by_name("test_role")

            mock_get.assert_called_once_with("test_role")
            assert result == sample_role

    @pytest.mark.asyncio
    async def test_get_all_roles(self, rbac_service, sample_role):
        """Test getting all roles."""
        with patch.object(
            rbac_service.rbac_repo.roles, "get_all", return_value=[sample_role]
        ) as mock_get:
            result = await rbac_service.get_all_roles()

            mock_get.assert_called_once()
            assert result == [sample_role]

    @pytest.mark.asyncio
    async def test_update_role(self, rbac_service, sample_role):
        """Test updating a role."""
        role_pk = uuid4()
        role_data = RoleUpdate(description="Updated description")

        with patch.object(
            rbac_service.rbac_repo.roles, "update_role", return_value=sample_role
        ) as mock_update:
            result = await rbac_service.update_role(role_pk, role_data)

            mock_update.assert_called_once_with(role_pk, role_data)
            assert result == sample_role

    @pytest.mark.asyncio
    async def test_delete_role(self, rbac_service):
        """Test deleting a role."""
        role_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.roles, "delete_by_pk", return_value=True
        ) as mock_delete:
            result = await rbac_service.delete_role(role_pk)

            mock_delete.assert_called_once_with(role_pk)
            assert result is True

    @pytest.mark.asyncio
    async def test_get_role_with_permissions(self, rbac_service):
        """Test getting role with permissions."""
        role_pk = uuid4()
        role_with_permissions = RoleWithPermissions(
            pk=role_pk,
            name="test_role",
            description="Test description",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            permissions=[],
        )

        with patch.object(
            rbac_service.rbac_repo.roles,
            "get_role_with_permissions",
            return_value=role_with_permissions,
        ) as mock_get:
            result = await rbac_service.get_role_with_permissions(role_pk)

            mock_get.assert_called_once_with(role_pk)
            assert result == role_with_permissions


class TestRBACServicePermissionManagement:
    """Test permission management methods."""

    @pytest.mark.asyncio
    async def test_create_permission(self, rbac_service, sample_permission):
        """Test creating a permission."""
        permission_data = PermissionCreate(
            name="test.permission", description="Test permission"
        )

        with patch.object(
            rbac_service.rbac_repo.permissions,
            "create_permission",
            return_value=sample_permission,
        ) as mock_create:
            result = await rbac_service.create_permission(permission_data)

            mock_create.assert_called_once_with(permission_data)
            assert result == sample_permission

    @pytest.mark.asyncio
    async def test_get_permission(self, rbac_service, sample_permission):
        """Test getting a permission by ID."""
        permission_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.permissions,
            "get_by_pk",
            return_value=sample_permission,
        ) as mock_get:
            result = await rbac_service.get_permission(permission_pk)

            mock_get.assert_called_once_with(permission_pk)
            assert result == sample_permission

    @pytest.mark.asyncio
    async def test_get_permission_by_name(self, rbac_service, sample_permission):
        """Test getting a permission by name."""
        with patch.object(
            rbac_service.rbac_repo.permissions,
            "get_by_name",
            return_value=sample_permission,
        ) as mock_get:
            result = await rbac_service.get_permission_by_name("test.permission")

            mock_get.assert_called_once_with("test.permission")
            assert result == sample_permission

    @pytest.mark.asyncio
    async def test_get_dynamic_permissions(
        self, rbac_service, sample_dynamic_permission
    ):
        """Test getting dynamic permissions."""
        with patch.object(
            rbac_service.rbac_repo.permissions,
            "get_dynamic_permissions",
            return_value=[sample_dynamic_permission],
        ) as mock_get:
            result = await rbac_service.get_dynamic_permissions()

            mock_get.assert_called_once()
            assert result == [sample_dynamic_permission]

    @pytest.mark.asyncio
    async def test_update_permission(self, rbac_service, sample_permission):
        """Test updating a permission."""
        permission_pk = uuid4()
        permission_data = PermissionUpdate(description="Updated description")

        with patch.object(
            rbac_service.rbac_repo.permissions,
            "update_permission",
            return_value=sample_permission,
        ) as mock_update:
            result = await rbac_service.update_permission(
                permission_pk, permission_data
            )

            mock_update.assert_called_once_with(permission_pk, permission_data)
            assert result == sample_permission

    @pytest.mark.asyncio
    async def test_delete_permission(self, rbac_service):
        """Test deleting a permission."""
        permission_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.permissions, "delete_by_pk", return_value=True
        ) as mock_delete:
            result = await rbac_service.delete_permission(permission_pk)

            mock_delete.assert_called_once_with(permission_pk)
            assert result is True


class TestRBACServiceRolePermissionManagement:
    """Test role-permission management methods."""

    @pytest.mark.asyncio
    async def test_assign_permission_to_role(self, rbac_service):
        """Test assigning permission to role."""
        role_pk = uuid4()
        permission_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.role_permissions,
            "assign_permission_to_role",
            return_value=MagicMock(),
        ) as mock_assign:
            result = await rbac_service.assign_permission_to_role(
                role_pk, permission_pk
            )

            mock_assign.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_remove_permission_from_role(self, rbac_service):
        """Test removing permission from role."""
        role_pk = uuid4()
        permission_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.role_permissions,
            "remove_permission_from_role",
            return_value=True,
        ) as mock_remove:
            result = await rbac_service.remove_permission_from_role(
                role_pk, permission_pk
            )

            mock_remove.assert_called_once_with(role_pk, permission_pk)
            assert result is True

    @pytest.mark.asyncio
    async def test_get_role_permissions(self, rbac_service, sample_permission):
        """Test getting role permissions."""
        role_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.role_permissions,
            "get_role_permissions",
            return_value=[sample_permission],
        ) as mock_get:
            result = await rbac_service.get_role_permissions(role_pk)

            mock_get.assert_called_once_with(role_pk)
            assert result == [sample_permission]


class TestRBACServiceUserRoleManagement:
    """Test user-role management methods."""

    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, rbac_service):
        """Test assigning role to user."""
        user_pk = uuid4()
        role_pk = uuid4()
        assigned_by_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.user_roles,
            "assign_role_to_user",
            return_value=MagicMock(),
        ) as mock_assign:
            result = await rbac_service.assign_role_to_user(
                user_pk, role_pk, assigned_by_pk
            )

            mock_assign.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_remove_role_from_user(self, rbac_service):
        """Test removing role from user."""
        user_pk = uuid4()
        role_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.user_roles,
            "remove_role_from_user",
            return_value=True,
        ) as mock_remove:
            result = await rbac_service.remove_role_from_user(user_pk, role_pk)

            mock_remove.assert_called_once_with(user_pk, role_pk)
            assert result is True

    @pytest.mark.asyncio
    async def test_get_user_roles(self, rbac_service, sample_role):
        """Test getting user roles."""
        user_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.user_roles,
            "get_user_roles",
            return_value=[sample_role],
        ) as mock_get:
            result = await rbac_service.get_user_roles(user_pk)

            mock_get.assert_called_once_with(user_pk)
            assert result == [sample_role]

    @pytest.mark.asyncio
    async def test_get_user_with_roles(self, rbac_service):
        """Test getting user with roles."""
        user_pk = uuid4()
        user_with_roles = UserWithRoles(user_pk=user_pk, roles=[], permissions=[])

        with patch.object(
            rbac_service.rbac_repo.user_roles,
            "get_user_with_roles",
            return_value=user_with_roles,
        ) as mock_get:
            result = await rbac_service.get_user_with_roles(user_pk)

            mock_get.assert_called_once_with(user_pk)
            assert result == user_with_roles


class TestRBACServiceUserPermissionManagement:
    """Test user permission management methods."""

    @pytest.mark.asyncio
    async def test_grant_permission_to_user(self, rbac_service):
        """Test granting permission to user."""
        user_pk = uuid4()
        permission_pk = uuid4()
        granted_by_user_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.user_permissions,
            "grant_permission_to_user",
            return_value=MagicMock(),
        ) as mock_grant:
            result = await rbac_service.grant_permission_to_user(
                user_pk, permission_pk, granted_by_user_pk=granted_by_user_pk
            )

            mock_grant.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_revoke_permission_from_user(self, rbac_service):
        """Test revoking permission from user."""
        user_pk = uuid4()
        permission_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.user_permissions,
            "revoke_permission_from_user",
            return_value=True,
        ) as mock_revoke:
            result = await rbac_service.revoke_permission_from_user(
                user_pk, permission_pk
            )

            mock_revoke.assert_called_once_with(user_pk, permission_pk)
            assert result is True

    @pytest.mark.asyncio
    async def test_get_user_permissions(self, rbac_service):
        """Test getting user permissions."""
        user_pk = uuid4()
        permission_summary = UserPermissionSummary(
            permission_name="test.permission", is_dynamic=False, source="role"
        )

        with patch.object(
            rbac_service.rbac_repo.user_roles,
            "get_user_permissions_summary",
            return_value=[permission_summary],
        ) as mock_get:
            result = await rbac_service.get_user_permissions(user_pk)

            mock_get.assert_called_once_with(user_pk)
            assert result == [permission_summary]


class TestRBACServicePermissionChecking:
    """Test permission checking methods."""

    @pytest.mark.asyncio
    async def test_has_permission_true(self, rbac_service):
        """Test checking permission when user has it."""
        user_pk = uuid4()
        permission_name = "test.permission"

        permission_summary = UserPermissionSummary(
            permission_name=permission_name,
            is_dynamic=False,
            expires_at=None,
            source="role",
        )

        with patch.object(
            rbac_service.rbac_repo.user_permissions, "has_permission", return_value=True
        ):
            with patch.object(
                rbac_service, "get_user_permissions", return_value=[permission_summary]
            ):
                result = await rbac_service.has_permission(user_pk, permission_name)

                assert result.has_permission is True
                assert result.source == "role"

    @pytest.mark.asyncio
    async def test_has_permission_false(self, rbac_service):
        """Test checking permission when user doesn't have it."""
        user_pk = uuid4()
        permission_name = "test.permission"

        with patch.object(
            rbac_service.rbac_repo.user_permissions,
            "has_permission",
            return_value=False,
        ):
            result = await rbac_service.has_permission(user_pk, permission_name)

            assert result.has_permission is False
            assert result.source is None

    @pytest.mark.asyncio
    async def test_check_multiple_permissions(self, rbac_service):
        """Test checking multiple permissions."""
        user_pk = uuid4()
        permission_names = ["perm1", "perm2"]

        with patch.object(
            rbac_service,
            "has_permission",
            side_effect=[
                PermissionCheckResult(has_permission=True),
                PermissionCheckResult(has_permission=False),
            ],
        ) as mock_check:
            result = await rbac_service.check_multiple_permissions(
                user_pk, permission_names
            )

            assert len(result) == 2
            assert result["perm1"].has_permission is True
            assert result["perm2"].has_permission is False
            assert mock_check.call_count == 2


class TestRBACServiceDynamicPermissions:
    """Test dynamic permission management methods."""

    @pytest.mark.asyncio
    async def test_grant_dynamic_permission_by_loyalty(
        self, rbac_service, sample_dynamic_permission
    ):
        """Test granting dynamic permissions based on loyalty score."""
        user_pk = uuid4()
        loyalty_score = 1000

        with patch.object(
            rbac_service,
            "get_permission_by_name",
            return_value=sample_dynamic_permission,
        ):
            with patch.object(
                rbac_service, "grant_permission_to_user", return_value=True
            ) as mock_grant:
                result = await rbac_service.grant_dynamic_permission_by_loyalty(
                    user_pk, loyalty_score
                )

                assert "topics.create_featured" in result
                mock_grant.assert_called()

    @pytest.mark.asyncio
    async def test_grant_dynamic_permission_low_score(self, rbac_service):
        """Test granting dynamic permissions with low loyalty score."""
        user_pk = uuid4()
        loyalty_score = 50

        result = await rbac_service.grant_dynamic_permission_by_loyalty(
            user_pk, loyalty_score
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_revoke_dynamic_permissions_below_threshold(
        self, rbac_service, sample_dynamic_permission
    ):
        """Test revoking dynamic permissions below threshold."""
        user_pk = uuid4()
        loyalty_score = 50

        with patch.object(
            rbac_service,
            "get_permission_by_name",
            return_value=sample_dynamic_permission,
        ):
            with patch.object(
                rbac_service, "revoke_permission_from_user", return_value=True
            ) as mock_revoke:
                result = await rbac_service.revoke_dynamic_permissions_below_threshold(
                    user_pk, loyalty_score
                )

                assert len(result) > 0
                mock_revoke.assert_called()


class TestRBACServiceUtilityMethods:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_permissions(self, rbac_service):
        """Test cleaning up expired permissions."""
        with patch.object(
            rbac_service.rbac_repo.user_permissions,
            "cleanup_expired_permissions",
            return_value=5,
        ) as mock_cleanup:
            result = await rbac_service.cleanup_expired_permissions()

            mock_cleanup.assert_called_once()
            assert result == 5

    @pytest.mark.asyncio
    async def test_get_permission_names_for_user(self, rbac_service):
        """Test getting permission names for user."""
        user_pk = uuid4()
        permission_summary = UserPermissionSummary(
            permission_name="test.permission", is_dynamic=False, source="role"
        )

        with patch.object(
            rbac_service, "get_user_permissions", return_value=[permission_summary]
        ):
            result = await rbac_service.get_permission_names_for_user(user_pk)

            assert result == ["test.permission"]

    @pytest.mark.asyncio
    async def test_is_user_admin_true(self, rbac_service):
        """Test checking if user is admin when they are."""
        user_pk = uuid4()
        admin_role = Role(
            pk=uuid4(),
            name="admin",
            description="Admin role",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(rbac_service, "get_user_roles", return_value=[admin_role]):
            result = await rbac_service.is_user_admin(user_pk)

            assert result is True

    @pytest.mark.asyncio
    async def test_is_user_admin_false(self, rbac_service):
        """Test checking if user is admin when they're not."""
        user_pk = uuid4()
        citizen_role = Role(
            pk=uuid4(),
            name="citizen",
            description="Citizen role",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(rbac_service, "get_user_roles", return_value=[citizen_role]):
            result = await rbac_service.is_user_admin(user_pk)

            assert result is False

    @pytest.mark.asyncio
    async def test_is_user_moderator_true(self, rbac_service):
        """Test checking if user is moderator when they are."""
        user_pk = uuid4()
        moderator_role = Role(
            pk=uuid4(),
            name="moderator",
            description="Moderator role",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(
            rbac_service, "get_user_roles", return_value=[moderator_role]
        ):
            result = await rbac_service.is_user_moderator(user_pk)

            assert result is True

    @pytest.mark.asyncio
    async def test_assign_default_citizen_role(self, rbac_service, sample_role):
        """Test assigning default citizen role."""
        user_pk = uuid4()
        citizen_role = Role(
            pk=uuid4(),
            name="citizen",
            description="Citizen role",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(rbac_service, "get_role_by_name", return_value=citizen_role):
            with patch.object(
                rbac_service, "assign_role_to_user", return_value=True
            ) as mock_assign:
                result = await rbac_service.assign_default_citizen_role(user_pk)

                mock_assign.assert_called_once_with(user_pk, citizen_role.pk)
                assert result is True

    @pytest.mark.asyncio
    async def test_assign_default_citizen_role_not_found(self, rbac_service):
        """Test assigning default citizen role when role not found."""
        user_pk = uuid4()

        with patch.object(rbac_service, "get_role_by_name", return_value=None):
            result = await rbac_service.assign_default_citizen_role(user_pk)

            assert result is False


class TestRBACServiceExceptionHandling:
    """Test exception handling in service methods."""

    @pytest.mark.asyncio
    async def test_create_role_exception_handling(self, rbac_service):
        """Test exception handling in create_role."""
        role_data = RoleCreate(name="test_role")

        with patch.object(
            rbac_service.rbac_repo.roles,
            "create_role",
            side_effect=Exception("Database error"),
        ):
            with pytest.raises(Exception):
                await rbac_service.create_role(role_data)

    @pytest.mark.asyncio
    async def test_assign_permission_to_role_exception(self, rbac_service):
        """Test exception handling in assign_permission_to_role."""
        role_pk = uuid4()
        permission_pk = uuid4()

        with patch.object(
            rbac_service.rbac_repo.role_permissions,
            "assign_permission_to_role",
            side_effect=Exception("Database error"),
        ):
            with pytest.raises(Exception):
                await rbac_service.assign_permission_to_role(role_pk, permission_pk)

    @pytest.mark.asyncio
    async def test_has_permission_exception_handling(self, rbac_service):
        """Test exception handling in has_permission."""
        user_pk = uuid4()
        permission_name = "test.permission"

        with patch.object(
            rbac_service.rbac_repo.user_permissions,
            "has_permission",
            side_effect=Exception("Database error"),
        ):
            with pytest.raises(Exception):
                await rbac_service.has_permission(user_pk, permission_name)
