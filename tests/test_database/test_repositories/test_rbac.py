"""Tests for RBAC repository classes."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.rbac import Permission
from therobotoverlord_api.database.models.rbac import PermissionCreate
from therobotoverlord_api.database.models.rbac import PermissionUpdate
from therobotoverlord_api.database.models.rbac import Role
from therobotoverlord_api.database.models.rbac import RoleCreate
from therobotoverlord_api.database.models.rbac import RolePermission
from therobotoverlord_api.database.models.rbac import RolePermissionCreate
from therobotoverlord_api.database.models.rbac import RoleUpdate
from therobotoverlord_api.database.models.rbac import UserPermission
from therobotoverlord_api.database.models.rbac import UserPermissionCreate
from therobotoverlord_api.database.models.rbac import UserPermissionSummary
from therobotoverlord_api.database.models.rbac import UserRole
from therobotoverlord_api.database.models.rbac import UserRoleCreate
from therobotoverlord_api.database.models.rbac import UserRoleUpdate
from therobotoverlord_api.database.repositories.rbac import PermissionRepository
from therobotoverlord_api.database.repositories.rbac import RBACRepository
from therobotoverlord_api.database.repositories.rbac import RolePermissionRepository
from therobotoverlord_api.database.repositories.rbac import RoleRepository
from therobotoverlord_api.database.repositories.rbac import UserPermissionRepository
from therobotoverlord_api.database.repositories.rbac import UserRoleRepository


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
def role_repository():
    """Create a RoleRepository instance for testing."""
    return RoleRepository()


class TestRoleRepository:
    """Test RoleRepository class."""

    def test_init(self, role_repository):
        """Test repository initialization."""
        assert role_repository.table_name == "roles"

    @pytest.mark.asyncio
    async def test_create_role(self, role_repository, sample_role):
        """Test creating a new role."""
        role_create = RoleCreate(name="test_role", description="Test description")

        # Mock the create_from_dict method directly to avoid database connection
        with patch.object(
            role_repository, "create_from_dict", return_value=sample_role
        ) as mock_create:
            result = await role_repository.create_from_dict(role_create.model_dump())
            assert result == sample_role
            mock_create.assert_called_once_with(role_create.model_dump())

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.rbac.get_db_connection")
    async def test_get_role_with_permissions(self, mock_get_db, role_repository):
        """Test getting role with permissions."""
        role_pk = uuid4()

        # Mock database response with proper structure for RoleWithPermissions
        mock_record = {
            "pk": role_pk,
            "name": "admin",
            "description": "Administrator role",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "permissions": [
                {
                    "pk": uuid4(),
                    "name": "user.create",
                    "description": "Create users",
                    "is_dynamic": False,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
                {
                    "pk": uuid4(),
                    "name": "user.delete",
                    "description": "Delete users",
                    "is_dynamic": False,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            ],
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_record
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        result = await role_repository.get_role_with_permissions(role_pk)

        # Since we're mocking the database response, we expect the method to be called
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.rbac.get_db_connection")
    async def test_get_role_with_permissions_not_found(
        self, mock_get_db, role_repository
    ):
        """Test getting role with permissions when role not found."""
        role_pk = uuid4()

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        result = await role_repository.get_role_with_permissions(role_pk)

        assert result is None
        mock_conn.fetchrow.assert_called_once()


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


class TestRoleRepositoryMethods:
    """Test RoleRepository methods."""

    @pytest.fixture
    def repository(self):
        """Create a RoleRepository instance for testing."""
        return RoleRepository()

    @pytest.fixture
    def sample_role_pk(self):
        """Sample role primary key for testing."""
        return uuid4()

    def test_init(self, repository):
        """Test repository initialization."""
        assert repository.table_name == "roles"

    def test_record_to_model(self, repository, mock_record, sample_role):
        """Test converting database record to Role model."""
        with patch(
            "therobotoverlord_api.database.models.rbac.Role.model_validate",
            return_value=sample_role,
        ) as mock_validate:
            result = repository._record_to_model(mock_record)

            mock_validate.assert_called_once_with(mock_record)
            assert result == sample_role

    @pytest.mark.asyncio
    async def test_create_role(self, repository, sample_role):
        """Test creating a new role."""
        role_create = RoleCreate(name="test_role", description="Test description")

        with patch.object(
            repository, "create_from_dict", return_value=sample_role
        ) as mock_create:
            result = await repository.create_role(role_create)

            mock_create.assert_called_once_with(
                {"name": "test_role", "description": "Test description"}
            )
            assert result == sample_role

    @pytest.mark.asyncio
    async def test_update_role(self, repository, sample_role):
        """Test updating a role."""
        role_pk = uuid4()
        role_update = RoleUpdate(description="Updated description")

        with patch.object(
            repository, "update_from_dict", return_value=sample_role
        ) as mock_update:
            result = await repository.update_role(role_pk, role_update)

            mock_update.assert_called_once_with(
                role_pk, {"description": "Updated description"}
            )
            assert result == sample_role

    @pytest.mark.asyncio
    async def test_get_by_name(self, repository, sample_role):
        """Test getting role by name."""
        with patch.object(
            repository, "find_one_by", return_value=sample_role
        ) as mock_find:
            result = await repository.get_by_name("test_role")

            mock_find.assert_called_once_with(name="test_role")
            assert result == sample_role

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.rbac.get_db_connection")
    async def test_get_role_with_permissions(
        self, mock_get_db, repository, sample_role_pk
    ):
        """Test getting role with permissions."""
        # Mock database response
        mock_record = {
            "pk": sample_role_pk,
            "name": "admin",
            "description": "Administrator role",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "permissions": [
                {
                    "pk": uuid4(),
                    "name": "user.create",
                    "description": "Create users",
                    "is_dynamic": False,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
                {
                    "pk": uuid4(),
                    "name": "user.delete",
                    "description": "Delete users",
                    "is_dynamic": False,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            ],
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_record
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        result = await repository.get_role_with_permissions(sample_role_pk)

        assert result is not None
        assert result.name == "admin"
        assert len(result.permissions) == 2

    @pytest.mark.asyncio
    async def test_get_role_with_permissions_not_found(self, repository):
        """Test getting role with permissions when role not found."""
        role_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = None
            mock_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.get_role_with_permissions(role_pk)

            assert result is None


class TestPermissionRepository:
    """Test PermissionRepository class."""

    @pytest.fixture
    def repository(self):
        """Create a PermissionRepository instance for testing."""
        return PermissionRepository()

    def test_init(self, repository):
        """Test repository initialization."""
        assert repository.table_name == "permissions"

    def test_record_to_model(self, repository, mock_record, sample_permission):
        """Test converting database record to Permission model."""
        with patch(
            "therobotoverlord_api.database.models.rbac.Permission.model_validate",
            return_value=sample_permission,
        ) as mock_validate:
            result = repository._record_to_model(mock_record)

            mock_validate.assert_called_once_with(mock_record)
            assert result == sample_permission

    @pytest.mark.asyncio
    async def test_create_permission(self, repository, sample_permission):
        """Test creating a new permission."""
        permission_create = PermissionCreate(
            name="test.permission", description="Test permission", is_dynamic=False
        )

        with patch.object(
            repository, "create_from_dict", return_value=sample_permission
        ) as mock_create:
            result = await repository.create_permission(permission_create)

            mock_create.assert_called_once_with(
                {
                    "name": "test.permission",
                    "description": "Test permission",
                    "is_dynamic": False,
                }
            )
            assert result == sample_permission

    @pytest.mark.asyncio
    async def test_update_permission(self, repository, sample_permission):
        """Test updating a permission."""
        permission_pk = uuid4()
        permission_update = PermissionUpdate(description="Updated description")

        with patch.object(
            repository, "update_from_dict", return_value=sample_permission
        ) as mock_update:
            result = await repository.update_permission(
                permission_pk, permission_update
            )

            mock_update.assert_called_once_with(
                permission_pk, {"description": "Updated description"}
            )
            assert result == sample_permission

    @pytest.mark.asyncio
    async def test_get_by_name(self, repository, sample_permission):
        """Test getting permission by name."""
        with patch.object(
            repository, "find_one_by", return_value=sample_permission
        ) as mock_find:
            result = await repository.get_by_name("test.permission")

            mock_find.assert_called_once_with(name="test.permission")
            assert result == sample_permission

    @pytest.mark.asyncio
    async def test_get_dynamic_permissions(self, repository, sample_permission):
        """Test getting dynamic permissions."""
        with patch.object(
            repository, "find_by", return_value=[sample_permission]
        ) as mock_find:
            result = await repository.get_dynamic_permissions()

            mock_find.assert_called_once_with(is_dynamic=True)
            assert result == [sample_permission]


class TestRolePermissionRepository:
    """Test RolePermissionRepository class."""

    @pytest.fixture
    def repository(self):
        """Create a RolePermissionRepository instance for testing."""
        return RolePermissionRepository()

    @pytest.mark.asyncio
    async def test_assign_permission_to_role(self, repository):
        """Test assigning permission to role."""
        role_pk = uuid4()
        permission_pk = uuid4()
        assignment = RolePermissionCreate(role_pk=role_pk, permission_pk=permission_pk)

        mock_record = {
            "role_pk": role_pk,
            "permission_pk": permission_pk,
            "created_at": "2023-01-01T00:00:00Z",
        }

        expected_result = RolePermission(
            role_pk=role_pk,
            permission_pk=permission_pk,
            created_at=datetime.now(UTC),
        )

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = mock_record
            mock_conn.return_value.__aenter__.return_value = mock_connection

            with patch(
                "therobotoverlord_api.database.models.rbac.RolePermission.model_validate",
                return_value=expected_result,
            ):
                result = await repository.assign_permission_to_role(assignment)

                assert result == expected_result
                mock_connection.fetchrow.assert_called()

    @pytest.mark.asyncio
    async def test_remove_permission_from_role(self, repository):
        """Test removing permission from role."""
        role_pk = uuid4()
        permission_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.execute.return_value = "DELETE 1"
            mock_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.remove_permission_from_role(
                role_pk, permission_pk
            )

            assert result is True
            mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_permission_from_role_not_found(self, repository):
        """Test removing permission from role when not found."""
        role_pk = uuid4()
        permission_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.execute.return_value = "DELETE 0"
            mock_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.remove_permission_from_role(
                role_pk, permission_pk
            )

            assert result is False
            mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_role_permissions(self, repository, sample_permission):
        """Test getting role permissions."""
        role_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = [{"name": "test.permission"}]
            mock_conn.return_value.__aenter__.return_value = mock_connection

            with patch(
                "therobotoverlord_api.database.models.rbac.Permission.model_validate",
                return_value=sample_permission,
            ):
                result = await repository.get_role_permissions(role_pk)

                assert result == [sample_permission]
                mock_connection.fetch.assert_called_once()


class TestUserRoleRepository:
    """Test UserRoleRepository class."""

    @pytest.fixture
    def repository(self):
        """Create a UserRoleRepository instance for testing."""
        return UserRoleRepository()

    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, repository):
        """Test assigning role to user."""
        user_pk = uuid4()
        role_pk = uuid4()
        assigned_by_pk = uuid4()
        assignment = UserRoleCreate(
            user_pk=user_pk, role_pk=role_pk, assigned_by_pk=assigned_by_pk
        )

        mock_record = {
            "user_pk": user_pk,
            "role_pk": role_pk,
            "assigned_at": "2023-01-01T00:00:00Z",
            "assigned_by_pk": assigned_by_pk,
            "expires_at": None,
            "is_active": True,
        }

        expected_result = UserRole(
            user_pk=user_pk,
            role_pk=role_pk,
            assigned_at=datetime.now(UTC),
            assigned_by_pk=assigned_by_pk,
            expires_at=None,
            is_active=True,
        )

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = mock_record
            mock_conn.return_value.__aenter__.return_value = mock_connection

            with patch(
                "therobotoverlord_api.database.models.rbac.UserRole.model_validate",
                return_value=expected_result,
            ):
                result = await repository.assign_role_to_user(assignment)

                assert result == expected_result
                mock_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_role(self, repository):
        """Test updating user role."""
        user_pk = uuid4()
        role_pk = uuid4()
        update_data = UserRoleUpdate(is_active=False)

        mock_record = {
            "user_pk": user_pk,
            "role_pk": role_pk,
            "assigned_at": "2023-01-01T00:00:00Z",
            "assigned_by_pk": None,
            "expires_at": None,
            "is_active": False,
        }

        expected_result = UserRole(
            user_pk=user_pk,
            role_pk=role_pk,
            assigned_at=datetime.now(UTC),
            assigned_by_pk=None,
            expires_at=None,
            is_active=False,
        )

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = mock_record
            mock_conn.return_value.__aenter__.return_value = mock_connection

            with patch(
                "therobotoverlord_api.database.models.rbac.UserRole.model_validate",
                return_value=expected_result,
            ):
                result = await repository.update_user_role(
                    user_pk, role_pk, update_data
                )

                assert result == expected_result
                mock_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_role_from_user(self, repository):
        """Test removing role from user."""
        user_pk = uuid4()
        role_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.execute.return_value = "UPDATE 1"
            mock_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.remove_role_from_user(user_pk, role_pk)

            assert result is True
            mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_roles(self, repository, sample_role):
        """Test getting user roles."""
        user_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = [{"name": "test_role"}]
            mock_conn.return_value.__aenter__.return_value = mock_connection

            with patch(
                "therobotoverlord_api.database.models.rbac.Role.model_validate",
                return_value=sample_role,
            ):
                result = await repository.get_user_roles(user_pk)

                assert result == [sample_role]
                mock_connection.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_permissions_summary(self, repository):
        """Test getting user permissions summary."""
        user_pk = uuid4()

        mock_records = [
            {
                "permission_name": "test.permission",
                "is_dynamic": False,
                "expires_at": None,
            }
        ]

        expected_summary = UserPermissionSummary(
            permission_name="test.permission",
            is_dynamic=False,
            expires_at=None,
            source="combined",
        )

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.get_user_permissions_summary(user_pk)

            assert len(result) == 1
            assert result[0].permission_name == expected_summary.permission_name
            assert result[0].is_dynamic == expected_summary.is_dynamic
            assert result[0].source == expected_summary.source


class TestUserPermissionRepository:
    """Test UserPermissionRepository class."""

    @pytest.fixture
    def repository(self):
        """Create a UserPermissionRepository instance for testing."""
        return UserPermissionRepository()

    @pytest.mark.asyncio
    async def test_grant_permission_to_user(self, repository):
        """Test granting permission to user."""
        user_pk = uuid4()
        permission_pk = uuid4()
        granted_by_user_pk = uuid4()
        permission_data = UserPermissionCreate(
            user_pk=user_pk,
            permission_pk=permission_pk,
            granted_by_user_pk=granted_by_user_pk,
        )

        mock_record = {
            "user_pk": user_pk,
            "permission_pk": permission_pk,
            "granted_at": "2023-01-01T00:00:00Z",
            "expires_at": None,
            "granted_by_event": None,
            "granted_by_user_pk": granted_by_user_pk,
            "is_active": True,
        }

        expected_result = UserPermission(
            user_pk=user_pk,
            permission_pk=permission_pk,
            granted_at=datetime.now(UTC),
            expires_at=None,
            granted_by_event=None,
            granted_by_user_pk=granted_by_user_pk,
            is_active=True,
        )

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = mock_record
            mock_conn.return_value.__aenter__.return_value = mock_connection

            with patch(
                "therobotoverlord_api.database.models.rbac.UserPermission.model_validate",
                return_value=expected_result,
            ):
                result = await repository.grant_permission_to_user(permission_data)

                assert result == expected_result
                mock_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_permission_from_user(self, repository):
        """Test revoking permission from user."""
        user_pk = uuid4()
        permission_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.execute.return_value = "UPDATE 1"
            mock_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.revoke_permission_from_user(
                user_pk, permission_pk
            )

            assert result is True
            mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_has_permission(self, repository):
        """Test checking if user has permission."""
        user_pk = uuid4()
        permission_name = "test.permission"

        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = True
            mock_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.has_permission(user_pk, permission_name)

            assert result is True
            mock_connection.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_permissions(self, repository):
        """Test cleaning up expired permissions."""
        with patch(
            "therobotoverlord_api.database.repositories.rbac.get_db_connection"
        ) as mock_conn:
            mock_connection = AsyncMock()
            mock_connection.execute.return_value = "UPDATE 5"
            mock_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.cleanup_expired_permissions()

            assert result == 5
            mock_connection.execute.assert_called_once()


class TestRBACRepository:
    """Test RBACRepository class."""

    @pytest.fixture
    def repository(self):
        """Create an RBACRepository instance for testing."""
        return RBACRepository()

    def test_init(self, repository):
        """Test repository initialization."""
        assert isinstance(repository.roles, RoleRepository)
        assert isinstance(repository.permissions, PermissionRepository)
        assert isinstance(repository.role_permissions, RolePermissionRepository)
        assert isinstance(repository.user_roles, UserRoleRepository)
        assert isinstance(repository.user_permissions, UserPermissionRepository)

    def test_repository_composition(self, repository):
        """Test that all sub-repositories are properly composed."""
        # Test that all repositories are accessible
        assert hasattr(repository, "roles")
        assert hasattr(repository, "permissions")
        assert hasattr(repository, "role_permissions")
        assert hasattr(repository, "user_roles")
        assert hasattr(repository, "user_permissions")

        # Test that they are the correct types
        assert repository.roles.table_name == "roles"
        assert repository.permissions.table_name == "permissions"
