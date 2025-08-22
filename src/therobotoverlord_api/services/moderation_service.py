"""Moderation service with real-time WebSocket notifications."""

import logging

from uuid import UUID

from therobotoverlord_api.database.connection import db
from therobotoverlord_api.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


def get_event_broadcaster(websocket_manager):
    """Get event broadcaster for WebSocket notifications."""
    from therobotoverlord_api.websocket.events import (
        get_event_broadcaster as _get_event_broadcaster,
    )

    return _get_event_broadcaster(websocket_manager)


class ModerationService:
    """Service for handling content moderation with real-time updates."""

    def __init__(self):
        self.db = db

    async def process_content_decision(
        self,
        content_id: UUID,
        content_type: str,
        user_id: UUID,
        decision: str,
        feedback: str | None = None,
        tags: list[str] | None = None,
        loyalty_score_change: int | None = None,
    ):
        """Process moderation decision and broadcast real-time updates."""
        try:
            # Update content status in database
            if content_type == "post":
                await self._update_post_status(content_id, decision, feedback)
            elif content_type == "topic":
                await self._update_topic_status(content_id, decision, feedback)

            # Update loyalty score if applicable
            if loyalty_score_change:
                await self._update_loyalty_score(user_id, loyalty_score_change)

            # Broadcast moderation result via WebSocket
            event_broadcaster = get_event_broadcaster(websocket_manager)
            await event_broadcaster.broadcast_content_moderation_result(
                user_id=user_id,
                content_id=content_id,
                content_type=content_type,
                decision=decision,
                feedback=feedback,
            )

            # Update queue position for remaining items
            await self._update_queue_positions(content_type, user_id)

            logger.info(
                f"Processed {decision} decision for {content_type} {content_id}"
            )

        except Exception as e:
            logger.error(f"Error processing moderation decision: {e}")
            raise

    async def _update_post_status(
        self, post_id: UUID, decision: str, feedback: str | None
    ):
        """Update post status in database."""
        status = "approved" if decision == "approved" else "rejected"
        query = """
            UPDATE posts
            SET status = $1, moderation_feedback = $2, moderated_at = NOW()
            WHERE pk = $3
        """
        await self.db.execute(query, status, feedback, post_id)

    async def _update_topic_status(
        self, topic_id: UUID, status: str, moderator_notes: str | None = None
    ):
        """Update topic status."""
        query = "UPDATE topics SET status = $1, moderator_notes = $2 WHERE pk = $3"
        await self.db.execute(query, status, moderator_notes, topic_id)

    async def _update_message_status(
        self, message_id: UUID, status: str, moderator_notes: str | None = None
    ):
        """Update private message status."""
        query = "UPDATE private_messages SET status = $1, moderator_notes = $2 WHERE pk = $3"
        await self.db.execute(query, status, moderator_notes, message_id)

    async def _update_loyalty_score(self, user_id: UUID, change: int):
        """Update user loyalty score."""
        query = """
            UPDATE users
            SET loyalty_score = loyalty_score + $1
            WHERE pk = $2
            RETURNING loyalty_score
        """
        result = await self.db.fetchrow(query, change, user_id)
        if result:
            new_score = result["loyalty_score"]

            # Broadcast loyalty score update
            event_broadcaster = get_event_broadcaster(websocket_manager)
            await event_broadcaster.broadcast_loyalty_score_update(
                user_id=user_id,
                old_score=new_score - change,
                new_score=new_score,
                reason="Content moderation result",
            )

    async def _update_queue_positions(
        self, content_type: str, user_id: UUID, websocket_manager=None
    ):
        """Update queue positions and broadcast updates."""
        try:
            # Get user's remaining items in queue
            if content_type == "post":
                queue_table = "post_moderation_queue"
                content_table = "posts"
            else:
                queue_table = "topic_creation_queue"
                content_table = "topics"

            query = f"""
                SELECT q.pk, q.position_in_queue, c.created_by_pk
                FROM {queue_table} q
                JOIN {content_table} c ON q.{content_type}_pk = c.pk
                WHERE c.created_by_pk = $1 AND q.status = 'pending'
                ORDER BY q.position_in_queue
            """

            results = await self.db.fetch(query, user_id)

            if results:
                # Get total queue size
                total_query = f"SELECT COUNT(*) as total FROM {queue_table} WHERE status = 'pending'"
                total_result = await self.db.fetchrow(total_query)
                total_size = total_result["total"] if total_result else 0

                # Broadcast position updates for user's remaining items
                event_broadcaster = get_event_broadcaster(websocket_manager)
                for i, _row in enumerate(results):
                    new_position = i + 1  # User's relative position in their own queue
                    await event_broadcaster.broadcast_queue_position_update(
                        user_id=user_id,
                        queue_type=f"{content_type}_moderation",
                        old_position=None,
                        new_position=new_position,
                        total_queue_size=total_size,
                    )

        except Exception as e:
            logger.warning(f"Failed to update queue positions: {e}")

    async def _get_content_info(
        self, content_id: UUID, content_type: str
    ) -> dict | None:
        """Get content information including user_id."""
        if content_type == "post":
            query = "SELECT user_pk, status FROM posts WHERE pk = $1"
        elif content_type == "topic":
            query = "SELECT user_pk, status FROM topics WHERE pk = $1"
        elif content_type == "private_message":
            query = "SELECT sender_pk as user_pk, status FROM private_messages WHERE pk = $1"
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

        return await self.db.fetchrow(query, content_id)

    async def approve_content(
        self,
        content_id: UUID,
        content_type: str,
        moderator_id: UUID,
        moderator_notes: str | None = None,
        websocket_manager=None,
    ) -> bool:
        """Approve content and broadcast WebSocket notification."""
        try:
            # Get content info to find user_id
            content_info = await self._get_content_info(content_id, content_type)
            if not content_info:
                logger.warning(f"Content {content_id} not found")
                return False

            user_id = content_info["user_pk"]

            # Check if content is already processed
            if content_info.get("status") == "approved":
                logger.info(f"Content {content_id} already approved")
                return True

            # Update content status
            if content_type == "post":
                await self._update_post_status(content_id, "approved", moderator_notes)
            elif content_type == "topic":
                await self._update_topic_status(content_id, "approved", moderator_notes)
            elif content_type == "private_message":
                await self._update_message_status(
                    content_id, "approved", moderator_notes
                )

            # Broadcast moderation result via WebSocket
            if websocket_manager:
                try:
                    event_broadcaster = get_event_broadcaster(websocket_manager)
                    await event_broadcaster.broadcast_content_moderation_result(
                        user_id=user_id,
                        content_id=content_id,
                        content_type=content_type,
                        decision="approved",
                        feedback=moderator_notes,
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast content approval: {e}")

            # Update queue positions for remaining items
            await self._update_queue_positions(content_type, user_id, websocket_manager)

            logger.info(f"Approved {content_type} {content_id}")
            return True

        except Exception as e:
            logger.error(f"Error approving content: {e}")
            raise

    async def reject_content(
        self,
        content_id: UUID,
        content_type: str,
        moderator_id: UUID,
        moderator_notes: str | None = None,
        websocket_manager=None,
    ) -> bool:
        """Reject content and broadcast WebSocket notification."""
        try:
            # Get content info to find user_id
            content_info = await self._get_content_info(content_id, content_type)
            if not content_info:
                logger.warning(f"Content {content_id} not found")
                return False

            user_id = content_info["user_pk"]

            # Update content status
            if content_type == "post":
                await self._update_post_status(content_id, "rejected", moderator_notes)
            elif content_type == "topic":
                await self._update_topic_status(content_id, "rejected", moderator_notes)
            elif content_type == "private_message":
                await self._update_message_status(
                    content_id, "rejected", moderator_notes
                )

            # Broadcast moderation result via WebSocket
            if websocket_manager:
                try:
                    event_broadcaster = get_event_broadcaster(websocket_manager)
                    await event_broadcaster.broadcast_content_moderation_result(
                        user_id=user_id,
                        content_id=content_id,
                        content_type=content_type,
                        decision="rejected",
                        feedback=moderator_notes,
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast content rejection: {e}")

            # Update queue position for remaining items
            await self._update_queue_positions(content_type, user_id)

            logger.info(f"Rejected {content_type} {content_id}")
            return True

        except Exception as e:
            logger.error(f"Error rejecting content: {e}")
            raise
