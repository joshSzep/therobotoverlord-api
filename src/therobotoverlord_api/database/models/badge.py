"""Badge models for The Robot Overlord API."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from therobotoverlord_api.database.models.base import BaseDBModel


class BadgeType(str, Enum):
    """Badge type enumeration."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class Badge(BaseDBModel):
    """Badge model."""

    name: str
    description: str
    image_url: str
    badge_type: BadgeType
    criteria_config: dict
    is_active: bool = True


class BadgeCreate(BaseModel):
    """Badge creation model."""

    name: str
    description: str
    image_url: str
    badge_type: BadgeType
    criteria_config: dict
    is_active: bool = True


class BadgeUpdate(BaseModel):
    """Badge update model."""

    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    badge_type: BadgeType | None = None
    criteria_config: dict | None = None
    is_active: bool | None = None


class UserBadge(BaseDBModel):
    """User badge model."""

    user_pk: UUID
    badge_pk: UUID
    awarded_at: datetime
    awarded_for_post_pk: UUID | None = None
    awarded_for_topic_pk: UUID | None = None
    awarded_by_event: str | None = None


class UserBadgeCreate(BaseModel):
    """User badge creation model."""

    user_pk: UUID
    badge_pk: UUID
    awarded_for_post_pk: UUID | None = None
    awarded_for_topic_pk: UUID | None = None
    awarded_by_event: str | None = None


class UserBadgeWithDetails(UserBadge):
    """User badge with badge details and username."""

    badge: Badge
    username: str | None = None


class UserBadgeSummary(BaseModel):
    """Summary of user's badges for public display."""

    user_pk: UUID
    username: str
    total_badges: int
    positive_badges: int
    negative_badges: int
    recent_badges: list[UserBadgeWithDetails] = Field(default_factory=list)


class BadgeEligibilityCheck(BaseModel):
    """Badge eligibility check result."""

    badge_pk: UUID
    badge_name: str
    is_eligible: bool
    current_progress: int
    required_progress: int
    criteria_met: bool
    reason: str | None = None
