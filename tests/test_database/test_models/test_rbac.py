"""Tests for RBAC database models."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

import pytest

from pydantic import ValidationError

from therobotoverlord_api.database.models.rbac import Permission
from therobotoverlord_api.database.models.rbac import PermissionCheckResult
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


class TestRole:
    """Test Role model."""

    def test_role_creation(self):
        """Test creating a valid role."""
        now = datetime.now(UTC)
        role = Role(
            pk=uuid4(),
            name="admin",
            description="Administrator role",
            created_at=now,
            updated_at=now,
        )

        assert role.name == "admin"
        assert role.description == "Administrator role"
        assert role.created_at == now
        assert role.updated_at == now

    def test_role_without_description(self):
        """Test creating a role without description."""
        now = datetime.now(UTC)
        role = Role(pk=uuid4(), name="citizen", created_at=now, updated_at=now)

        assert role.name == "citizen"
        assert role.description is None

    def test_role_create_model(self):
        """Test RoleCreate model."""
        role_create = RoleCreate(name="moderator", description="Content moderator")

        assert role_create.name == "moderator"
        assert role_create.description == "Content moderator"

    def test_role_create_without_description(self):
        """Test RoleCreate without description."""
        role_create = RoleCreate(name="citizen")

        assert role_create.name == "citizen"
        assert role_create.description is None

    def test_role_update_model(self):
        """Test RoleUpdate model."""
        role_update = RoleUpdate(description="Updated description")

        assert role_update.description == "Updated description"

    def test_role_validation_empty_name(self):
        """Test role validation with empty name."""
        with pytest.raises(ValidationError):
            RoleCreate(name="")


class TestPermission:
    """Test Permission model."""

    def test_permission_creation(self):
        """Test creating a valid permission."""
        now = datetime.now(UTC)
        permission = Permission(
            pk=uuid4(),
            name="posts.create",
            description="Create new posts",
            is_dynamic=False,
            created_at=now,
            updated_at=now,
        )

        assert permission.name == "posts.create"
        assert permission.description == "Create new posts"
        assert permission.is_dynamic is False

    def test_permission_dynamic(self):
        """Test creating a dynamic permission."""
        now = datetime.now(UTC)
        permission = Permission(
            pk=uuid4(),
            name="posts.create_premium",
            description="Create premium posts",
            is_dynamic=True,
            created_at=now,
            updated_at=now,
        )

        assert permission.is_dynamic is True

    def test_permission_create_model(self):
        """Test PermissionCreate model."""
        permission_create = PermissionCreate(
            name="topics.delete", description="Delete topics", is_dynamic=False
        )

        assert permission_create.name == "topics.delete"
        assert permission_create.description == "Delete topics"
        assert permission_create.is_dynamic is False

    def test_permission_create_defaults(self):
        """Test PermissionCreate with defaults."""
        permission_create = PermissionCreate(name="basic.permission")

        assert permission_create.name == "basic.permission"
        assert permission_create.description is None
        assert permission_create.is_dynamic is False

    def test_permission_update_model(self):
        """Test PermissionUpdate model."""
        permission_update = PermissionUpdate(
            description="Updated description", is_dynamic=True
        )

        assert permission_update.description == "Updated description"
        assert permission_update.is_dynamic is True


class TestRolePermission:
    """Test RolePermission model."""

    def test_role_permission_creation(self):
        """Test creating a role-permission relationship."""
        now = datetime.now(UTC)
        role_pk = uuid4()
        permission_pk = uuid4()

        role_permission = RolePermission(
            role_pk=role_pk, permission_pk=permission_pk, created_at=now
        )

        assert role_permission.role_pk == role_pk
        assert role_permission.permission_pk == permission_pk
        assert role_permission.created_at == now

    def test_role_permission_create_model(self):
        """Test RolePermissionCreate model."""
        role_pk = uuid4()
        permission_pk = uuid4()

        role_permission_create = RolePermissionCreate(
            role_pk=role_pk, permission_pk=permission_pk
        )

        assert role_permission_create.role_pk == role_pk
        assert role_permission_create.permission_pk == permission_pk


class TestUserRole:
    """Test UserRole model."""

    def test_user_role_creation(self):
        """Test creating a user-role relationship."""
        now = datetime.now(UTC)
        user_pk = uuid4()
        role_pk = uuid4()
        assigned_by_pk = uuid4()
        expires_at = datetime.now(UTC)

        user_role = UserRole(
            user_pk=user_pk,
            role_pk=role_pk,
            assigned_at=now,
            assigned_by_pk=assigned_by_pk,
            expires_at=expires_at,
            is_active=True,
        )

        assert user_role.user_pk == user_pk
        assert user_role.role_pk == role_pk
        assert user_role.assigned_at == now
        assert user_role.assigned_by_pk == assigned_by_pk
        assert user_role.expires_at == expires_at
        assert user_role.is_active is True

    def test_user_role_defaults(self):
        """Test UserRole with default values."""
        now = datetime.now(UTC)
        user_pk = uuid4()
        role_pk = uuid4()

        user_role = UserRole(user_pk=user_pk, role_pk=role_pk, assigned_at=now)

        assert user_role.assigned_by_pk is None
        assert user_role.expires_at is None
        assert user_role.is_active is True

    def test_user_role_create_model(self):
        """Test UserRoleCreate model."""
        user_pk = uuid4()
        role_pk = uuid4()
        assigned_by_pk = uuid4()
        expires_at = datetime.now(UTC)

        user_role_create = UserRoleCreate(
            user_pk=user_pk,
            role_pk=role_pk,
            assigned_by_pk=assigned_by_pk,
            expires_at=expires_at,
        )

        assert user_role_create.user_pk == user_pk
        assert user_role_create.role_pk == role_pk
        assert user_role_create.assigned_by_pk == assigned_by_pk
        assert user_role_create.expires_at == expires_at

    def test_user_role_update_model(self):
        """Test UserRoleUpdate model."""
        expires_at = datetime.now(UTC)

        user_role_update = UserRoleUpdate(expires_at=expires_at, is_active=False)

        assert user_role_update.expires_at == expires_at
        assert user_role_update.is_active is False


class TestUserPermission:
    """Test UserPermission model."""

    def test_user_permission_creation(self):
        """Test creating a user permission."""
        now = datetime.now(UTC)
        user_pk = uuid4()
        permission_pk = uuid4()
        granted_by_user_pk = uuid4()
        expires_at = datetime.now(UTC)

        user_permission = UserPermission(
            user_pk=user_pk,
            permission_pk=permission_pk,
            granted_at=now,
            expires_at=expires_at,
            granted_by_event="loyalty_score_1000",
            granted_by_user_pk=granted_by_user_pk,
            is_active=True,
        )

        assert user_permission.user_pk == user_pk
        assert user_permission.permission_pk == permission_pk
        assert user_permission.granted_at == now
        assert user_permission.expires_at == expires_at
        assert user_permission.granted_by_event == "loyalty_score_1000"
        assert user_permission.granted_by_user_pk == granted_by_user_pk
        assert user_permission.is_active is True

    def test_user_permission_defaults(self):
        """Test UserPermission with default values."""
        now = datetime.now(UTC)
        user_pk = uuid4()
        permission_pk = uuid4()

        user_permission = UserPermission(
            user_pk=user_pk, permission_pk=permission_pk, granted_at=now
        )

        assert user_permission.expires_at is None
        assert user_permission.granted_by_event is None
        assert user_permission.granted_by_user_pk is None
        assert user_permission.is_active is True

    def test_user_permission_create_model(self):
        """Test UserPermissionCreate model."""
        user_pk = uuid4()
        permission_pk = uuid4()
        granted_by_user_pk = uuid4()
        expires_at = datetime.now(UTC)

        user_permission_create = UserPermissionCreate(
            user_pk=user_pk,
            permission_pk=permission_pk,
            expires_at=expires_at,
            granted_by_event="manual_grant",
            granted_by_user_pk=granted_by_user_pk,
        )

        assert user_permission_create.user_pk == user_pk
        assert user_permission_create.permission_pk == permission_pk
        assert user_permission_create.expires_at == expires_at
        assert user_permission_create.granted_by_event == "manual_grant"
        assert user_permission_create.granted_by_user_pk == granted_by_user_pk

    def test_user_permission_update_model(self):
        """Test UserPermissionUpdate model."""
        expires_at = datetime.now(UTC)

        user_permission_update = UserPermissionUpdate(
            expires_at=expires_at, is_active=False
        )

        assert user_permission_update.expires_at == expires_at
        assert user_permission_update.is_active is False


class TestUserPermissionSummary:
    """Test UserPermissionSummary model."""

    def test_user_permission_summary_creation(self):
        """Test creating a user permission summary."""
        expires_at = datetime.now(UTC)

        summary = UserPermissionSummary(
            permission_name="posts.create",
            is_dynamic=False,
            expires_at=expires_at,
            source="role",
        )

        assert summary.permission_name == "posts.create"
        assert summary.is_dynamic is False
        assert summary.expires_at == expires_at
        assert summary.source == "role"

    def test_user_permission_summary_defaults(self):
        """Test UserPermissionSummary with defaults."""
        summary = UserPermissionSummary(
            permission_name="topics.create", is_dynamic=True, source="direct"
        )

        assert summary.permission_name == "topics.create"
        assert summary.is_dynamic is True
        assert summary.expires_at is None
        assert summary.source == "direct"


class TestRoleWithPermissions:
    """Test RoleWithPermissions model."""

    def test_role_with_permissions_creation(self):
        """Test creating a role with permissions."""
        now = datetime.now(UTC)
        role_pk = uuid4()

        permission1 = Permission(
            pk=uuid4(),
            name="posts.create",
            description="Create posts",
            is_dynamic=False,
            created_at=now,
            updated_at=now,
        )

        permission2 = Permission(
            pk=uuid4(),
            name="posts.edit_own",
            description="Edit own posts",
            is_dynamic=False,
            created_at=now,
            updated_at=now,
        )

        role_with_permissions = RoleWithPermissions(
            pk=role_pk,
            name="citizen",
            description="Regular user",
            created_at=now,
            updated_at=now,
            permissions=[permission1, permission2],
        )

        assert role_with_permissions.pk == role_pk
        assert role_with_permissions.name == "citizen"
        assert len(role_with_permissions.permissions) == 2
        assert role_with_permissions.permissions[0].name == "posts.create"
        assert role_with_permissions.permissions[1].name == "posts.edit_own"


class TestUserWithRoles:
    """Test UserWithRoles model."""

    def test_user_with_roles_creation(self):
        """Test creating a user with roles."""
        now = datetime.now(UTC)
        user_pk = uuid4()

        role = Role(
            pk=uuid4(),
            name="citizen",
            description="Regular user",
            created_at=now,
            updated_at=now,
        )

        permission_summary = UserPermissionSummary(
            permission_name="posts.create", is_dynamic=False, source="role"
        )

        user_with_roles = UserWithRoles(
            user_pk=user_pk, roles=[role], permissions=[permission_summary]
        )

        assert user_with_roles.user_pk == user_pk
        assert len(user_with_roles.roles) == 1
        assert user_with_roles.roles[0].name == "citizen"
        assert len(user_with_roles.permissions) == 1
        assert user_with_roles.permissions[0].permission_name == "posts.create"


class TestPermissionCheckResult:
    """Test PermissionCheckResult model."""

    def test_permission_check_result_creation(self):
        """Test creating a permission check result."""
        expires_at = datetime.now(UTC)

        result = PermissionCheckResult(
            has_permission=True, expires_at=expires_at, source="role"
        )

        assert result.has_permission is True
        assert result.expires_at == expires_at
        assert result.source == "role"

    def test_permission_check_result_defaults(self):
        """Test PermissionCheckResult with defaults."""
        result = PermissionCheckResult(has_permission=False)

        assert result.has_permission is False
        assert result.expires_at is None
        assert result.source is None

    def test_permission_check_result_no_permission(self):
        """Test permission check result for denied permission."""
        result = PermissionCheckResult(has_permission=False)

        assert result.has_permission is False
        assert result.expires_at is None
        assert result.source is None


class TestModelValidation:
    """Test model validation edge cases."""

    def test_invalid_uuid_fields(self):
        """Test validation with invalid UUID fields."""
        with pytest.raises(ValidationError):
            # This should raise a ValidationError due to invalid UUID format
            # We need to bypass pydantic's validation by using model_validate with invalid data
            RolePermissionCreate.model_validate(
                {"role_pk": "invalid-uuid", "permission_pk": str(uuid4())}
            )

    def test_empty_permission_name(self):
        """Test validation with empty permission name."""
        with pytest.raises(ValidationError):
            Permission(
                pk=uuid4(),
                name="",
                description="Test permission",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

    def test_valid_source_values(self):
        """Test UserPermissionSummary with various source values."""
        # Valid sources
        summary1 = UserPermissionSummary(
            permission_name="test.permission", is_dynamic=False, source="role"
        )
        assert summary1.source == "role"

        summary2 = UserPermissionSummary(
            permission_name="test.permission", is_dynamic=False, source="direct"
        )
        assert summary2.source == "direct"

        summary3 = UserPermissionSummary(
            permission_name="test.permission", is_dynamic=False, source="combined"
        )
        assert summary3.source == "combined"

    def test_model_serialization(self):
        """Test model serialization to dict."""
        role_create = RoleCreate(name="test_role", description="Test role description")

        data = role_create.model_dump()
        assert data["name"] == "test_role"
        assert data["description"] == "Test role description"

    def test_model_exclude_unset(self):
        """Test model serialization excluding unset fields."""
        role_update = RoleUpdate(description="Updated description")

        data = role_update.model_dump(exclude_unset=True)
        assert "description" in data
        assert data["description"] == "Updated description"
        # Other fields should not be present since they weren't set
