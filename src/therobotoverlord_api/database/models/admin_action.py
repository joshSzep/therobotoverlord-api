"""Admin action audit trail model for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from therobotoverlord_api.database.models.base import BaseDBModel


class AdminActionType(str, Enum):
    """Admin action type enumeration."""

    DASHBOARD_ACCESS = "dashboard_access"
    USER_ROLE_CHANGE = "user_role_change"
    USER_BAN = "user_ban"
    USER_UNBAN = "user_unban"
    SANCTION_APPLY = "sanction_apply"
    SANCTION_REMOVE = "sanction_remove"
    CONTENT_RESTORE = "content_restore"
    CONTENT_DELETE = "content_delete"
    APPEAL_DECISION = "appeal_decision"
    FLAG_DECISION = "flag_decision"
    SYSTEM_CONFIG = "system_config"
    BULK_ACTION = "bulk_action"


class AdminAction(BaseDBModel):
    """Track administrative actions for audit trail."""

    admin_pk: UUID
    action_type: AdminActionType
    target_type: str | None = None  # user, post, topic, etc.
    target_pk: UUID | None = None
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None


class AdminActionCreate(BaseModel):
    """Model for creating admin actions."""

    admin_pk: UUID
    action_type: AdminActionType
    target_type: str | None = None
    target_pk: UUID | None = None
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AdminActionResponse(BaseModel):
    """Response model for admin actions."""

    pk: UUID
    admin_pk: UUID
    action_type: AdminActionType
    target_type: str | None
    target_pk: UUID | None
    description: str
    metadata: dict[str, Any]
    ip_address: str | None
    created_at: datetime


class AuditLogResponse(BaseModel):
    """Response model for audit log listing."""

    actions: list[AdminActionResponse]
    total_count: int
    limit: int
    offset: int
