"""Private message models for The Robot Overlord."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from therobotoverlord_api.database.models.base import ContentStatus


class PrivateMessage(BaseModel):
    """Private message between users."""

    pk: UUID
    sender_pk: UUID
    recipient_pk: UUID
    content: str
    status: ContentStatus = ContentStatus.SUBMITTED
    sent_at: datetime
    read_at: datetime | None = None
    moderated_at: datetime | None = None
    moderator_feedback: str | None = None
    conversation_id: str  # Format: "users_{min_user_id}_{max_user_id}"

    model_config = ConfigDict(from_attributes=True)


class PrivateMessageCreate(BaseModel):
    """Model for creating a new private message."""

    recipient_pk: UUID
    content: str = Field(..., min_length=1, max_length=2000)
    sender_pk: UUID | None = None  # Set by API from current user

    model_config = ConfigDict(from_attributes=True)


class PrivateMessageUpdate(BaseModel):
    """Model for updating a private message."""

    content: str | None = Field(None, min_length=1, max_length=2000)
    status: ContentStatus | None = None
    read_at: datetime | None = None
    moderator_feedback: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PrivateMessageWithParticipants(BaseModel):
    """Private message with sender and recipient information."""

    pk: UUID
    sender_pk: UUID
    sender_username: str
    sender_display_name: str | None
    recipient_pk: UUID
    recipient_username: str
    recipient_display_name: str | None
    content: str
    status: ContentStatus
    sent_at: datetime
    read_at: datetime | None = None
    moderated_at: datetime | None = None
    moderator_feedback: str | None = None
    conversation_id: str

    model_config = ConfigDict(from_attributes=True)


class ConversationSummary(BaseModel):
    """Summary of a conversation between two users."""

    conversation_id: str
    other_user_pk: UUID
    other_user_username: str
    other_user_display_name: str | None
    last_message_content: str
    last_message_sent_at: datetime
    last_message_sender_pk: UUID
    unread_count: int
    total_messages: int

    model_config = ConfigDict(from_attributes=True)


class MessageThread(BaseModel):
    """Paginated conversation thread."""

    conversation_id: str
    messages: list[PrivateMessageWithParticipants]
    total_count: int
    has_more: bool
    other_user_pk: UUID
    other_user_username: str
    other_user_display_name: str | None

    model_config = ConfigDict(from_attributes=True)


class UnreadMessageCount(BaseModel):
    """Unread message count for a user."""

    total_unread: int
    conversations_with_unread: int

    model_config = ConfigDict(from_attributes=True)


class MessageSearchResult(BaseModel):
    """Search result for messages."""

    message: PrivateMessageWithParticipants
    conversation_id: str
    match_snippet: str | None = None

    model_config = ConfigDict(from_attributes=True)
