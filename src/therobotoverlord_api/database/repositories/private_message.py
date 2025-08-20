"""Private message repository for The Robot Overlord."""

import logging

from datetime import UTC
from datetime import datetime
from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.private_message import ConversationSummary
from therobotoverlord_api.database.models.private_message import MessageSearchResult
from therobotoverlord_api.database.models.private_message import MessageThread
from therobotoverlord_api.database.models.private_message import PrivateMessage
from therobotoverlord_api.database.models.private_message import PrivateMessageCreate
from therobotoverlord_api.database.models.private_message import (
    PrivateMessageWithParticipants,
)
from therobotoverlord_api.database.models.private_message import UnreadMessageCount
from therobotoverlord_api.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PrivateMessageRepository(BaseRepository[PrivateMessage]):
    """Repository for private message operations."""

    def __init__(self):
        super().__init__("private_messages")

    def _generate_conversation_id(self, user1_pk: UUID, user2_pk: UUID) -> str:
        """Generate consistent conversation ID for two users."""
        min_id = min(str(user1_pk), str(user2_pk))
        max_id = max(str(user1_pk), str(user2_pk))
        return f"users_{min_id}_{max_id}"

    def _record_to_model(self, record: Record) -> PrivateMessage:
        return PrivateMessage.model_validate(record)

    async def create_message(
        self, message_data: PrivateMessageCreate
    ) -> PrivateMessage | None:
        """Create a new private message."""
        try:
            # Generate conversation ID
            if message_data.sender_pk and message_data.recipient_pk:
                conversation_id = self._generate_conversation_id(
                    message_data.sender_pk, message_data.recipient_pk
                )
            else:
                logger.error("Missing sender or recipient PK")
                return None

            # Prepare message data
            message_dict = message_data.model_dump()
            message_dict.update(
                {
                    "conversation_id": conversation_id,
                    "sent_at": datetime.now(UTC),
                    "status": ContentStatus.SUBMITTED,  # Will be moderated
                }
            )

            query = """
                INSERT INTO private_messages
                (sender_pk, recipient_pk, content, conversation_id, sent_at, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            """

            async with get_db_connection() as connection:
                record = await connection.fetchrow(
                    query,
                    message_dict["sender_pk"],
                    message_dict["recipient_pk"],
                    message_dict["content"],
                    message_dict["conversation_id"],
                    message_dict["sent_at"],
                    message_dict["status"],
                )

            return PrivateMessage.model_validate(record) if record else None

        except Exception:
            logger.exception("Error creating private message")
            return None

    async def get_conversation(
        self,
        user1_pk: UUID,
        user2_pk: UUID,
        limit: int = 50,
        offset: int = 0,
        *,
        include_moderated: bool = False,
    ) -> MessageThread | None:
        """Get conversation between two users."""
        try:
            conversation_id = self._generate_conversation_id(user1_pk, user2_pk)

            # Build status filter
            status_filter = "AND pm.status IN ('approved', 'in_transit')"
            if include_moderated:
                status_filter = ""  # Include all statuses

            # Get messages with participant info
            query = f"""
                SELECT
                    pm.*,
                    sender.username as sender_username,
                    sender.display_name as sender_display_name,
                    recipient.username as recipient_username,
                    recipient.display_name as recipient_display_name
                FROM private_messages pm
                JOIN users sender ON pm.sender_pk = sender.pk
                JOIN users recipient ON pm.recipient_pk = recipient.pk
                WHERE pm.conversation_id = $1 {status_filter}
                ORDER BY pm.sent_at DESC
                LIMIT $2 OFFSET $3
            """

            async with get_db_connection() as connection:
                records = await connection.fetch(query, conversation_id, limit, offset)

                # Get total count
                count_query = f"""
                    SELECT COUNT(*)
                    FROM private_messages pm
                    WHERE pm.conversation_id = $1 {status_filter}
                """
                total_count = await connection.fetchval(count_query, conversation_id)

                # Get other user info
                other_user_pk = user2_pk if user1_pk != user2_pk else user1_pk
                other_user_query = """
                    SELECT username, display_name
                    FROM users
                    WHERE pk = $1
                """
                other_user = await connection.fetchrow(other_user_query, other_user_pk)

            if not other_user or total_count is None:
                return None

            messages = [
                PrivateMessageWithParticipants.model_validate(record)
                for record in records
            ]

            return MessageThread(
                conversation_id=conversation_id,
                messages=messages,
                total_count=int(total_count),
                has_more=(offset + len(messages)) < int(total_count),
                other_user_pk=other_user_pk,
                other_user_username=other_user["username"],
                other_user_display_name=other_user["display_name"],
            )

        except Exception:
            logger.exception(
                f"Error getting conversation between {user1_pk} and {user2_pk}"
            )
            return None

    async def get_user_conversations(
        self, user_pk: UUID, limit: int = 20, offset: int = 0
    ) -> list[ConversationSummary]:
        """Get list of conversations for a user."""
        try:
            query = """
                WITH latest_messages AS (
                    SELECT DISTINCT ON (pm.conversation_id)
                        pm.conversation_id,
                        pm.content as last_message_content,
                        pm.sent_at as last_message_sent_at,
                        pm.sender_pk as last_message_sender_pk,
                        CASE
                            WHEN pm.sender_pk = $1 THEN pm.recipient_pk
                            ELSE pm.sender_pk
                        END as other_user_pk
                    FROM private_messages pm
                    WHERE (pm.sender_pk = $1 OR pm.recipient_pk = $1)
                        AND pm.status IN ('approved', 'in_transit')
                    ORDER BY pm.conversation_id, pm.sent_at DESC
                ),
                unread_counts AS (
                    SELECT
                        pm.conversation_id,
                        COUNT(*) as unread_count
                    FROM private_messages pm
                    WHERE pm.recipient_pk = $1
                        AND pm.read_at IS NULL
                        AND pm.status = 'approved'
                    GROUP BY pm.conversation_id
                ),
                total_counts AS (
                    SELECT
                        pm.conversation_id,
                        COUNT(*) as total_messages
                    FROM private_messages pm
                    WHERE (pm.sender_pk = $1 OR pm.recipient_pk = $1)
                        AND pm.status IN ('approved', 'in_transit')
                    GROUP BY pm.conversation_id
                )
                SELECT
                    lm.conversation_id,
                    lm.other_user_pk,
                    u.username as other_user_username,
                    u.display_name as other_user_display_name,
                    lm.last_message_content,
                    lm.last_message_sent_at,
                    lm.last_message_sender_pk,
                    COALESCE(uc.unread_count, 0) as unread_count,
                    tc.total_messages
                FROM latest_messages lm
                JOIN users u ON lm.other_user_pk = u.pk
                LEFT JOIN unread_counts uc ON lm.conversation_id = uc.conversation_id
                JOIN total_counts tc ON lm.conversation_id = tc.conversation_id
                ORDER BY lm.last_message_sent_at DESC
                LIMIT $2 OFFSET $3
            """

            async with get_db_connection() as connection:
                records = await connection.fetch(query, user_pk, limit, offset)
            return [ConversationSummary.model_validate(record) for record in records]

        except Exception:
            logger.exception(f"Error getting conversations for user {user_pk}")
            return []

    async def mark_as_read(self, message_id: UUID, user_pk: UUID) -> bool:
        """Mark a message as read by the recipient."""
        try:
            query = """
                UPDATE private_messages
                SET read_at = $1
                WHERE pk = $2
                    AND recipient_pk = $3
                    AND read_at IS NULL
                    AND status = 'approved'
            """

            async with get_db_connection() as connection:
                result = await connection.execute(
                    query, datetime.now(UTC), message_id, user_pk
                )
            return result == "UPDATE 1"

        except Exception:
            logger.exception(f"Error marking message {message_id} as read")
            return False

    async def mark_conversation_as_read(self, user1_pk: UUID, user2_pk: UUID) -> int:
        """Mark all messages in a conversation as read for the current user."""
        try:
            conversation_id = self._generate_conversation_id(user1_pk, user2_pk)

            query = """
                UPDATE private_messages
                SET read_at = $1
                WHERE conversation_id = $2
                    AND recipient_pk = $3
                    AND read_at IS NULL
                    AND status = 'approved'
            """

            async with get_db_connection() as connection:
                result = await connection.execute(
                    query, datetime.now(UTC), conversation_id, user1_pk
                )
            # Extract number of updated rows from result string like "UPDATE 5"
            return int(result.split()[-1]) if result.startswith("UPDATE") else 0

        except Exception:
            logger.exception(f"Error marking conversation as read for user {user1_pk}")
            return 0

    async def get_unread_count(self, user_pk: UUID) -> UnreadMessageCount:
        """Get unread message count for a user."""
        try:
            query = """
                SELECT
                    COUNT(*) as total_unread,
                    COUNT(DISTINCT conversation_id) as conversations_with_unread
                FROM private_messages
                WHERE recipient_pk = $1
                    AND read_at IS NULL
                    AND status = 'approved'
            """

            async with get_db_connection() as connection:
                record = await connection.fetchrow(query, user_pk)
            return (
                UnreadMessageCount.model_validate(record)
                if record
                else UnreadMessageCount(total_unread=0, conversations_with_unread=0)
            )

        except Exception:
            logger.exception(f"Error getting unread count for user {user_pk}")
            return UnreadMessageCount(total_unread=0, conversations_with_unread=0)

    async def search_messages(
        self, user_pk: UUID, search_term: str, limit: int = 20, offset: int = 0
    ) -> list[MessageSearchResult]:
        """Search messages for a user."""
        try:
            query = """
                SELECT
                    pm.*,
                    sender.username as sender_username,
                    sender.display_name as sender_display_name,
                    recipient.username as recipient_username,
                    recipient.display_name as recipient_display_name,
                    ts_headline('english', pm.content, plainto_tsquery('english', $2)) as match_snippet
                FROM private_messages pm
                JOIN users sender ON pm.sender_pk = sender.pk
                JOIN users recipient ON pm.recipient_pk = recipient.pk
                WHERE (pm.sender_pk = $1 OR pm.recipient_pk = $1)
                    AND pm.status IN ('approved', 'in_transit')
                    AND to_tsvector('english', pm.content) @@ plainto_tsquery('english', $2)
                ORDER BY pm.sent_at DESC
                LIMIT $3 OFFSET $4
            """

            async with get_db_connection() as connection:
                records = await connection.fetch(
                    query, user_pk, search_term, limit, offset
                )

            results = []
            for record in records:
                message = PrivateMessageWithParticipants.model_validate(record)
                results.append(
                    MessageSearchResult(
                        message=message,
                        conversation_id=record["conversation_id"],
                        match_snippet=record.get("match_snippet"),
                    )
                )

            return results

        except Exception:
            logger.exception(f"Error searching messages for user {user_pk}")
            return []

    async def approve_message(
        self, message_id: UUID, feedback: str | None = None
    ) -> PrivateMessage | None:
        """Approve a private message after moderation."""
        try:
            query = """
                UPDATE private_messages
                SET status = $1, moderated_at = $2, moderator_feedback = $3
                WHERE pk = $4 AND status = 'submitted'
                RETURNING *
            """

            async with get_db_connection() as connection:
                record = await connection.fetchrow(
                    query,
                    ContentStatus.APPROVED,
                    datetime.now(UTC),
                    feedback,
                    message_id,
                )

            return PrivateMessage.model_validate(record) if record else None

        except Exception:
            logger.exception(f"Error approving message {message_id}")
            return None

    async def reject_message(
        self, message_id: UUID, feedback: str
    ) -> PrivateMessage | None:
        """Reject a private message after moderation."""
        try:
            query = """
                UPDATE private_messages
                SET status = $1, moderated_at = $2, moderator_feedback = $3
                WHERE pk = $4 AND status = 'submitted'
                RETURNING *
            """

            async with get_db_connection() as connection:
                record = await connection.fetchrow(
                    query,
                    ContentStatus.REJECTED,
                    datetime.now(UTC),
                    feedback,
                    message_id,
                )

            return PrivateMessage.model_validate(record) if record else None

        except Exception:
            logger.exception(f"Error rejecting message {message_id}")
            return None

    async def get_messages_for_moderation(
        self, limit: int = 50, offset: int = 0
    ) -> list[PrivateMessageWithParticipants]:
        """Get messages pending moderation."""
        try:
            query = """
                SELECT
                    pm.*,
                    sender.username as sender_username,
                    sender.display_name as sender_display_name,
                    recipient.username as recipient_username,
                    recipient.display_name as recipient_display_name
                FROM private_messages pm
                JOIN users sender ON pm.sender_pk = sender.pk
                JOIN users recipient ON pm.recipient_pk = recipient.pk
                WHERE pm.status = 'submitted'
                ORDER BY pm.sent_at ASC
                LIMIT $1 OFFSET $2
            """

            async with get_db_connection() as connection:
                records = await connection.fetch(query, limit, offset)
            return [
                PrivateMessageWithParticipants.model_validate(record)
                for record in records
            ]

        except Exception:
            logger.exception("Error getting messages for moderation")
            return []

    async def delete_message(
        self, message_id: UUID, user_pk: UUID, *, is_admin: bool = False
    ) -> bool:
        """Delete a message (soft delete by setting status to rejected)."""
        try:
            # Only allow deletion by sender or admin
            if is_admin:
                condition = "pk = $1"
                params: list[UUID | datetime] = [message_id]
            else:
                condition = "pk = $1 AND sender_pk = $2"
                params = [message_id, user_pk]

            query = f"""
                UPDATE private_messages
                SET status = 'rejected', moderated_at = $3
                WHERE {condition}
            """
            params.append(datetime.now(UTC))

            async with get_db_connection() as connection:
                result = await connection.execute(query, *params)
            return result == "UPDATE 1"

        except Exception:
            logger.exception(f"Error deleting message {message_id}")
            return False
