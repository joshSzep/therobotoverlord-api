"""System announcement model for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import UserRole


class AnnouncementType(str, Enum):
    """Announcement type enumeration."""

    MAINTENANCE = "maintenance"
    FEATURE_UPDATE = "feature_update"
    POLICY_CHANGE = "policy_change"
    GENERAL = "general"
    EMERGENCY = "emergency"


class SystemAnnouncement(BaseDBModel):
    """System-wide announcements."""

    title: str
    content: str
    announcement_type: AnnouncementType
    created_by_pk: UUID
    is_active: bool = True
    expires_at: datetime | None = None
    target_roles: list[UserRole] = Field(default_factory=list)


class AnnouncementCreate(BaseModel):
    """Model for creating system announcements."""

    title: str
    content: str
    announcement_type: AnnouncementType
    expires_at: datetime | None = None
    target_roles: list[UserRole] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AnnouncementResponse(BaseModel):
    """Response model for system announcements."""

    pk: UUID
    title: str
    content: str
    announcement_type: AnnouncementType
    created_by_pk: UUID
    is_active: bool
    expires_at: datetime | None
    target_roles: list[UserRole]
    created_at: datetime
    updated_at: datetime | None
