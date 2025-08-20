"""RBAC (Role-Based Access Control) database models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import field_validator

from therobotoverlord_api.database.models.base import BaseDBModel


class Role(BaseDBModel):
    """Role database model."""

    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate role name is not empty."""
        if not v or not v.strip():
            raise ValueError("Role name cannot be empty")
        return v.strip()


class RoleCreate(BaseModel):
    """Role creation model."""

    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate role name is not empty."""
        if not v or not v.strip():
            raise ValueError("Role name cannot be empty")
        return v.strip()


class RoleUpdate(BaseModel):
    """Role update model."""

    description: str | None = None


class Permission(BaseDBModel):
    """Permission database model."""

    name: str
    description: str | None = None
    is_dynamic: bool = False
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate permission name is not empty."""
        if not v or not v.strip():
            raise ValueError("Permission name cannot be empty")
        return v.strip()


class PermissionCreate(BaseModel):
    """Permission creation model."""

    name: str
    description: str | None = None
    is_dynamic: bool = False


class PermissionUpdate(BaseModel):
    """Permission update model."""

    description: str | None = None
    is_dynamic: bool | None = None


class RolePermission(BaseModel):
    """Role-Permission junction model."""

    role_pk: UUID
    permission_pk: UUID
    created_at: datetime


class RolePermissionCreate(BaseModel):
    """Role-Permission creation model."""

    role_pk: UUID
    permission_pk: UUID


class UserRole(BaseModel):
    """User-Role junction model."""

    user_pk: UUID
    role_pk: UUID
    assigned_at: datetime
    assigned_by_pk: UUID | None = None
    expires_at: datetime | None = None
    is_active: bool = True


class UserRoleCreate(BaseModel):
    """User-Role creation model."""

    user_pk: UUID
    role_pk: UUID
    assigned_by_pk: UUID | None = None
    expires_at: datetime | None = None


class UserRoleUpdate(BaseModel):
    """User-Role update model."""

    expires_at: datetime | None = None
    is_active: bool | None = None


class UserPermission(BaseModel):
    """User-Permission junction model."""

    user_pk: UUID
    permission_pk: UUID
    granted_at: datetime
    expires_at: datetime | None = None
    granted_by_event: str | None = None
    granted_by_user_pk: UUID | None = None
    is_active: bool = True


class UserPermissionCreate(BaseModel):
    """User permission creation model."""

    user_pk: UUID
    permission_pk: UUID
    expires_at: datetime | None = None
    granted_by_event: str | None = None
    granted_by_user_pk: UUID | None = None


class UserPermissionUpdate(BaseModel):
    """User permission update model."""

    expires_at: datetime | None = None
    is_active: bool | None = None


class UserPermissionSummary(BaseModel):
    """User permission summary for API responses."""

    permission_name: str
    is_dynamic: bool
    expires_at: datetime | None = None
    source: str  # 'role' or 'direct'


class RoleWithPermissions(BaseModel):
    """Role with associated permissions."""

    pk: UUID
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    permissions: list[Permission]


class UserWithRoles(BaseModel):
    """User with associated roles."""

    user_pk: UUID
    roles: list[Role]
    permissions: list[UserPermissionSummary]


class PermissionCheck(BaseModel):
    """Permission check request model."""

    user_pk: UUID
    permission_name: str


class PermissionCheckResult(BaseModel):
    """Permission check result model."""

    has_permission: bool
    expires_at: datetime | None = None
    source: str | None = None  # 'role' or 'direct'
