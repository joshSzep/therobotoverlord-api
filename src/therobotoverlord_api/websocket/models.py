"""WebSocket message models and types."""

from datetime import UTC
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class WebSocketEventType(str, Enum):
    """WebSocket event types."""

    # Connection events
    CONNECT = "connect"
    DISCONNECT = "disconnect"

    # Queue events
    QUEUE_POSITION_UPDATE = "queue_position_update"
    QUEUE_STATUS_CHANGE = "queue_status_change"

    # Moderation events
    CONTENT_APPROVED = "content_approved"
    CONTENT_REJECTED = "content_rejected"
    CONTENT_FLAGGED = "content_flagged"

    # Chat events
    OVERLORD_MESSAGE = "overlord_message"
    CHAT_RESPONSE = "chat_response"

    # User events
    LOYALTY_SCORE_UPDATE = "loyalty_score_update"
    RANK_CHANGE = "rank_change"
    BADGE_EARNED = "badge_earned"

    # System events
    ANNOUNCEMENT = "announcement"
    MAINTENANCE_MODE = "maintenance_mode"

    # Activity events
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""

    event_type: WebSocketEventType
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_id: UUID | None = None
    message_id: str | None = None


class QueuePositionUpdate(BaseModel):
    """Queue position update message."""

    queue_type: str
    old_position: int | None
    new_position: int
    estimated_wait_time: int | None  # seconds
    total_queue_size: int


class ContentModerationUpdate(BaseModel):
    """Content moderation decision update."""

    content_id: UUID
    content_type: str  # post, comment, etc.
    decision: str  # approved, rejected, flagged
    feedback: str | None = None
    tags: list[str] = []
    loyalty_score_change: int | None = None


class OverlordChatMessage(BaseModel):
    """Overlord chat message."""

    message: str
    response_to: UUID | None = None
    conversation_id: UUID | None = None
    metadata: dict[str, Any] = {}


class LoyaltyScoreUpdate(BaseModel):
    """Loyalty score update message."""

    old_score: int
    new_score: int
    change: int
    reason: str
    old_rank: str | None = None
    new_rank: str | None = None


class SystemAnnouncement(BaseModel):
    """System announcement message."""

    title: str
    message: str
    announcement_type: str
    priority: str = "normal"  # low, normal, high, critical
    expires_at: datetime | None = None


class UserActivityUpdate(BaseModel):
    """User activity status update."""

    user_id: UUID
    username: str
    status: str  # online, offline, away
    last_seen: datetime | None = None


class WebSocketConnectionInfo(BaseModel):
    """WebSocket connection information."""

    connection_id: str
    user_id: UUID
    connected_at: datetime
    last_ping: datetime
    subscriptions: list[str] = []  # List of channels/topics subscribed to
