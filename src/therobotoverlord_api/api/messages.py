"""Private messaging API endpoints for The Robot Overlord."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_role
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.private_message import ConversationSummary
from therobotoverlord_api.database.models.private_message import MessageSearchResult
from therobotoverlord_api.database.models.private_message import MessageThread
from therobotoverlord_api.database.models.private_message import PrivateMessage
from therobotoverlord_api.database.models.private_message import PrivateMessageCreate
from therobotoverlord_api.database.models.private_message import (
    PrivateMessageWithParticipants,
)
from therobotoverlord_api.database.models.private_message import UnreadMessageCount
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.repositories.private_message import (
    PrivateMessageRepository,
)
from therobotoverlord_api.services.queue_service import get_queue_service

router = APIRouter(prefix="/messages", tags=["messages"])

# Create dependency instances
moderator_dependency = require_role(UserRole.MODERATOR)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: PrivateMessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> PrivateMessage:
    """Send a new private message."""
    message_repo = PrivateMessageRepository()

    # Validate user can send messages (not banned/sanctioned)
    if current_user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Banned users cannot send messages",
        )

    if current_user.is_sanctioned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sanctioned users cannot send messages",
        )

    # Prevent self-messaging
    if message_data.recipient_pk == current_user.pk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send message to yourself",
        )

    # Set sender from current user
    message_data.sender_pk = current_user.pk

    # Create message
    message = await message_repo.create_message(message_data)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create message",
        )

    # Add to moderation queue
    queue_service = await get_queue_service()
    queue_id = await queue_service.add_message_to_queue(
        message.pk, message.sender_pk, message.recipient_pk, priority=0
    )

    if not queue_id:
        # If queue addition fails, log but don't fail the request
        # The message is still created and will be processed eventually
        pass

    return message


@router.get("/conversations")
async def get_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(le=50, ge=1)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ConversationSummary]:
    """Get list of conversations for the current user."""
    message_repo = PrivateMessageRepository()
    return await message_repo.get_user_conversations(current_user.pk, limit, offset)


@router.get("/conversations/{other_user_id}")
async def get_conversation(
    other_user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MessageThread:
    """Get conversation between current user and another user."""
    message_repo = PrivateMessageRepository()

    # Check if user is trying to view their own "conversation"
    if other_user_id == current_user.pk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot view conversation with yourself",
        )

    # Moderators can view any conversation for moderation purposes
    is_moderator = current_user.role in [
        UserRole.MODERATOR,
        UserRole.ADMIN,
        UserRole.SUPERADMIN,
    ]

    conversation = await message_repo.get_conversation(
        current_user.pk, other_user_id, limit, offset, include_moderated=is_moderator
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


@router.patch("/conversations/{other_user_id}/read")
async def mark_conversation_as_read(
    other_user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, int]:
    """Mark all messages in a conversation as read."""
    message_repo = PrivateMessageRepository()

    if other_user_id == current_user.pk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark conversation with yourself as read",
        )

    messages_marked = await message_repo.mark_conversation_as_read(
        current_user.pk, other_user_id
    )

    return {"messages_marked_read": messages_marked}


@router.patch("/{message_id}/read")
async def mark_message_as_read(
    message_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, bool]:
    """Mark a specific message as read."""
    message_repo = PrivateMessageRepository()

    success = await message_repo.mark_as_read(message_id, current_user.pk)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or already read",
        )

    return {"marked_as_read": True}


@router.get("/unread/count")
async def get_unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UnreadMessageCount:
    """Get unread message count for the current user."""
    message_repo = PrivateMessageRepository()
    return await message_repo.get_unread_count(current_user.pk)


@router.get("/search")
async def search_messages(
    current_user: Annotated[User, Depends(get_current_user)],
    q: Annotated[str, Query(min_length=2, max_length=100)],
    limit: Annotated[int, Query(le=50, ge=1)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MessageSearchResult]:
    """Search messages for the current user."""
    message_repo = PrivateMessageRepository()
    return await message_repo.search_messages(current_user.pk, q, limit, offset)


@router.delete("/{message_id}")
async def delete_message(
    message_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, bool]:
    """Delete a message (sender only, or admin)."""
    message_repo = PrivateMessageRepository()

    is_admin = current_user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]

    success = await message_repo.delete_message(
        message_id, current_user.pk, is_admin=is_admin
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have permission to delete it",
        )

    return {"deleted": True}


# Moderation endpoints
@router.get("/pending/list")
async def get_pending_messages(
    _: Annotated[User, Depends(moderator_dependency)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PrivateMessageWithParticipants]:
    """Get messages pending moderation (moderator+ only)."""
    message_repo = PrivateMessageRepository()
    return await message_repo.get_messages_for_moderation(limit, offset)


@router.patch("/{message_id}/approve")
async def approve_message(
    message_id: UUID,
    _: Annotated[User, Depends(moderator_dependency)],
    overlord_feedback: Annotated[str | None, Query(max_length=500)] = None,
) -> PrivateMessage:
    """Approve a message (moderator+ only)."""
    message_repo = PrivateMessageRepository()

    approved_message = await message_repo.approve_message(message_id, overlord_feedback)
    if not approved_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or already processed",
        )

    return approved_message


@router.patch("/{message_id}/reject")
async def reject_message(
    message_id: UUID,
    overlord_feedback: Annotated[str, Query(max_length=500)],
    _: Annotated[User, Depends(moderator_dependency)],
) -> PrivateMessage:
    """Reject a message with feedback (moderator+ only)."""
    message_repo = PrivateMessageRepository()

    rejected_message = await message_repo.reject_message(message_id, overlord_feedback)
    if not rejected_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or already processed",
        )

    return rejected_message


# Admin-only conversation viewing
@router.get("/admin/conversations/{user1_id}/{user2_id}")
async def admin_view_conversation(
    user1_id: UUID,
    user2_id: UUID,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MessageThread:
    """View any conversation between two users (admin+ only)."""
    message_repo = PrivateMessageRepository()

    if user1_id == user2_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot view conversation between same user",
        )

    conversation = await message_repo.get_conversation(
        user1_id, user2_id, limit, offset, include_moderated=True
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation
