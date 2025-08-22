"""Dashboard snapshot model for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from therobotoverlord_api.database.models.base import BaseDBModel


class DashboardSnapshotType(str, Enum):
    """Dashboard snapshot type enumeration."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DashboardSnapshot(BaseDBModel):
    """Periodic snapshots of dashboard metrics for historical tracking."""

    snapshot_type: DashboardSnapshotType
    metrics_data: dict[str, Any]
    period_start: datetime
    period_end: datetime
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DashboardSnapshotCreate(BaseModel):
    """Model for creating dashboard snapshots."""

    snapshot_type: DashboardSnapshotType
    metrics_data: dict[str, Any]
    period_start: datetime
    period_end: datetime
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserSummary(BaseModel):
    """User summary for dashboard display."""

    pk: UUID
    username: str
    role: str
    loyalty_score: int | None = None


class UserActivitySummary(BaseModel):
    """User activity summary from existing user/loyalty systems."""

    total_users: int
    active_users_24h: int
    active_users_7d: int
    new_registrations_24h: int
    banned_users: int
    sanctioned_users: int
    top_contributors: list[UserSummary]


class ContentActivitySummary(BaseModel):
    """Content activity summary from existing content systems."""

    posts_created_24h: int
    posts_approved_24h: int
    posts_rejected_24h: int
    topics_created_24h: int
    flags_submitted_24h: int
    appeals_submitted_24h: int
    moderation_queue_size: int


class ModerationActivitySummary(BaseModel):
    """Moderation activity summary from existing moderation systems."""

    flags_pending: int
    appeals_pending: int
    sanctions_applied_24h: int
    moderator_actions_24h: int
    queue_processing_times: dict[str, float]


class SystemHealthSummary(BaseModel):
    """System health summary from existing health endpoints."""

    overall_status: str
    database_healthy: bool
    redis_healthy: bool
    queue_healthy: bool
    worker_status: dict[str, str]
    response_time_avg: float


class RecentActivity(BaseModel):
    """Recent administrative activity."""

    activity_type: str
    description: str
    user_id: UUID | None = None
    moderator_id: UUID | None = None
    timestamp: datetime


class DashboardOverview(BaseModel):
    """Aggregated dashboard overview data."""

    user_metrics: UserActivitySummary
    content_metrics: ContentActivitySummary
    moderation_metrics: ModerationActivitySummary
    system_health: SystemHealthSummary
    recent_activity: list[RecentActivity]
    generated_at: datetime
