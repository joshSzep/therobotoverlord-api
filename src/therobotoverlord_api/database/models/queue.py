"""Queue models for The Robot Overlord API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import QueueStatus


class BaseQueueModel(BaseDBModel):
    """Base queue model with common fields."""

    priority_score: int
    priority: int = 0
    position_in_queue: int
    status: QueueStatus = QueueStatus.PENDING
    entered_queue_at: datetime
    estimated_completion_at: datetime | None = None
    worker_assigned_at: datetime | None = None
    worker_id: str | None = None


class TopicCreationQueue(BaseQueueModel):
    """Topic creation queue model."""

    topic_pk: UUID


class PostTosScreeningQueue(BaseQueueModel):
    """Post ToS screening queue model."""

    post_pk: UUID
    topic_pk: UUID


class PostModerationQueue(BaseQueueModel):
    """Post moderation queue model."""

    post_pk: UUID
    topic_pk: UUID


class PrivateMessageQueue(BaseQueueModel):
    """Private message queue model."""

    message_pk: UUID
    sender_pk: UUID
    recipient_pk: UUID
    conversation_id: str


class QueueItemCreate(BaseModel):
    """Base queue item creation model."""

    priority_score: int
    priority: int = 0
    position_in_queue: int
    entered_queue_at: datetime
    estimated_completion_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TopicCreationQueueCreate(QueueItemCreate):
    """Topic creation queue item creation model."""

    topic_pk: UUID


class PostTosScreeningQueueCreate(QueueItemCreate):
    """Post ToS screening queue item creation model."""

    post_pk: UUID
    topic_pk: UUID


class PostModerationQueueCreate(QueueItemCreate):
    """Post moderation queue item creation model."""

    post_pk: UUID
    topic_pk: UUID


class PrivateMessageQueueCreate(QueueItemCreate):
    """Private message queue item creation model."""

    message_pk: UUID
    sender_pk: UUID
    recipient_pk: UUID
    conversation_id: str


class QueueItemUpdate(BaseModel):
    """Base queue item update model."""

    priority_score: int | None = None
    priority: int | None = None
    position_in_queue: int | None = None
    status: QueueStatus | None = None
    estimated_completion_at: datetime | None = None
    worker_assigned_at: datetime | None = None
    worker_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class QueueStatusInfo(BaseModel):
    """Queue status information for users."""

    queue_type: str
    position: int
    total_items: int
    estimated_wait_minutes: int | None = None
    status: QueueStatus
    overlord_commentary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class QueueOverview(BaseModel):
    """Public queue overview statistics."""

    topic_creation_queue_length: int
    post_tos_screening_queue_length: int
    post_moderation_queue_length: int
    private_message_queue_length: int
    average_processing_time_minutes: int | None = None
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


class QueueWithContent(BaseModel):
    """Queue item with associated content for processing."""

    pk: UUID
    queue_type: str
    content_pk: UUID
    content_type: str
    priority_score: int
    position_in_queue: int
    status: QueueStatus
    entered_queue_at: datetime
    worker_assigned_at: datetime | None
    worker_id: str | None

    model_config = ConfigDict(from_attributes=True)
