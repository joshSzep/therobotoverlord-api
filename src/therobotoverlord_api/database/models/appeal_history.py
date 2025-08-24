"""Appeal history database models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class AppealHistoryAction(str, Enum):
    """Appeal history action types."""

    SUBMITTED = "submitted"
    ASSIGNED = "assigned"
    UNDER_REVIEW = "under_review"
    SUSTAINED = "sustained"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    CONTENT_RESTORED = "content_restored"
    SANCTION_APPLIED = "sanction_applied"


class AppealHistoryEntry(BaseModel):
    """Appeal history entry model."""

    model_config = ConfigDict(from_attributes=True)

    pk: UUID
    appeal_pk: UUID
    action: AppealHistoryAction
    actor_pk: UUID | None = None
    actor_username: str | None = None
    details: dict[str, Any] | None = None
    notes: str | None = None
    created_at: datetime


class AppealHistoryCreate(BaseModel):
    """Appeal history creation model."""

    appeal_pk: UUID
    action: AppealHistoryAction
    actor_pk: UUID | None = None
    details: dict[str, Any] | None = None
    notes: str | None = None


class AppealStatusSummary(BaseModel):
    """Appeal status summary model."""

    appeal_pk: UUID
    current_status: str
    submitted_at: datetime
    last_updated: datetime
    assigned_to: str | None = None
    resolution_time_hours: float | None = None
    total_history_entries: int
    key_milestones: list[dict[str, Any]]
