"""Sanction models for The Robot Overlord API."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import SanctionSeverity


class SanctionType(str, Enum):
    """Types of sanctions that can be applied to users."""

    WARNING = "warning"
    TEMPORARY_BAN = "temporary_ban"
    PERMANENT_BAN = "permanent_ban"
    POST_RESTRICTION = "post_restriction"
    TOPIC_RESTRICTION = "topic_restriction"
    POSTING_FREEZE = "posting_freeze"
    RATE_LIMIT = "rate_limit"


class Sanction(BaseDBModel):
    """Sanction database model."""

    user_pk: UUID
    sanction_type: SanctionType  # Match DB column name
    severity: SanctionSeverity = SanctionSeverity.MINOR  # Add missing field
    applied_by_pk: UUID
    applied_at: datetime
    expires_at: datetime | None = None
    reason: str
    is_active: bool = True


class SanctionCreate(BaseModel):
    """Sanction creation model."""

    user_pk: UUID
    sanction_type: SanctionType
    severity: SanctionSeverity = SanctionSeverity.MINOR
    expires_at: datetime | None = None
    reason: str

    model_config = ConfigDict(from_attributes=True)


class SanctionUpdate(BaseModel):
    """Sanction update model."""

    is_active: bool | None = None
    severity: SanctionSeverity | None = None
    reason: str | None = None
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SanctionWithDetails(BaseModel):
    """Sanction with user details for admin views."""

    pk: UUID
    user_pk: UUID
    username: str
    sanction_type: SanctionType
    severity: SanctionSeverity
    applied_by_pk: UUID
    applied_by_username: str
    applied_at: datetime
    expires_at: datetime | None = None
    reason: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
