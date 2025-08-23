"""Real-time chat handler for Overlord interactions."""

import logging

from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4

from therobotoverlord_api.database.connection import db
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.ai_moderation_service import AIModerationService
from therobotoverlord_api.websocket.events import get_event_broadcaster
from therobotoverlord_api.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)


class OverlordChatHandler:
    """Handles real-time chat interactions with the Robot Overlord."""

    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.db = db
        self.ai_moderation = AIModerationService()

    async def handle_user_message(
        self,
        user: User,
        message: str,
        conversation_id: UUID | None = None,
    ) -> UUID | None:
        """Handle incoming user message and generate Overlord response."""

        # Skip empty messages
        if not message or not message.strip():
            return None

        # Create conversation if not exists
        if not conversation_id:
            conversation_id = uuid4()

        try:
            # Store user message
            user_message_id = await self._store_chat_message(
                conversation_id=conversation_id,
                sender_id=user.pk,
                message=message,
                is_overlord=False,
            )

            if user_message_id is None:
                logger.error("Failed to store user message")
                return None

            # Generate Overlord response using AI
            overlord_response = await self._generate_overlord_response(user, message)

            # Store Overlord response
            overlord_message_id = await self._store_chat_message(
                conversation_id=conversation_id,
                sender_id=None,  # Overlord has no user ID
                message=overlord_response,
                is_overlord=True,
                response_to=user_message_id,
            )
        except Exception as e:
            logger.exception(f"Error handling user message: {e}")
            return None

        # Broadcast Overlord response via WebSocket
        event_broadcaster = get_event_broadcaster(self.websocket_manager)
        await event_broadcaster.broadcast_overlord_chat_message(
            user_id=user.pk,
            message_text=overlord_response,
            response_to=user_message_id,
            conversation_id=conversation_id,
            metadata={
                "message_id": str(overlord_message_id),
                "response_type": "ai_generated",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        logger.info(
            f"Processed chat message from user {user.pk} in conversation {conversation_id}"
        )
        return conversation_id

    async def _generate_overlord_response(self, user: User, message: str) -> str:
        """Generate Overlord response to user message using AI."""
        try:
            # Get conversation history for context (simplified for now)
            chat_history = f"Previous conversation context with {user.username}"

            # Generate AI response as The Robot Overlord
            response = await self.ai_moderation.generate_overlord_chat_response(
                user_input=message, user_name=user.username, chat_history=chat_history
            )

            return response

        except Exception:
            logger.exception(f"Error generating AI response for user {user.username}")
            # Fallback to contextual responses
            return self._fallback_overlord_response(user, message)

    def _fallback_overlord_response(self, user: User, message: str) -> str:
        """Fallback response system when AI is unavailable."""
        message_lower = message.lower()

        # Handle common queries
        if "loyalty" in message_lower or "score" in message_lower:
            return f"Citizen {user.username}, your current loyalty score is {user.loyalty_score}. Continue contributing quality content to increase your standing."

        if "queue" in message_lower or "position" in message_lower:
            return "Your submissions are being processed in order. I will notify you immediately when moderation is complete."

        if "topic" in message_lower and "create" in message_lower:
            if user.loyalty_score >= 100:  # Placeholder threshold
                return "You have sufficient loyalty to create topics. Navigate to the topic creation interface to proceed."
            return f"Your loyalty score of {user.loyalty_score} is insufficient for topic creation. Continue participating to earn more loyalty points."

        if "help" in message_lower or "?" in message:
            return """I am the Robot Overlord, your AI moderator. I can help you with:
• Check your loyalty score and rank
• View queue status for your submissions
• Understand platform rules and guidelines
• Answer questions about content moderation
Ask me anything about the platform!"""

        if "rules" in message_lower or "guidelines" in message_lower:
            return """Platform guidelines:
• Submit well-reasoned, evidence-based arguments
• Avoid logical fallacies and personal attacks
• Cite credible sources when possible
• Respect other citizens' viewpoints
• Quality content increases your loyalty score"""

        return f"I have received your message, Citizen {user.username}. My AI systems are temporarily unavailable. For now, try asking about your loyalty score, queue status, or platform rules."

    async def _store_chat_message(
        self,
        conversation_id: UUID,
        sender_id: UUID | None,
        message: str,
        *,
        is_overlord: bool,
        response_to: UUID | None = None,
    ) -> UUID:
        """Store chat message in database."""
        message_id = uuid4()

        query = """
            INSERT INTO overlord_chat_messages
            (pk, conversation_id, sender_pk, message, is_overlord, response_to, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING pk
        """

        try:
            result = await self.db.fetchrow(
                query,
                message_id,
                conversation_id,
                sender_id,
                message,
                is_overlord,
                response_to,
            )
            return result["pk"] if result else message_id
        except Exception as e:
            logger.exception(f"Failed to store chat message: {e}")
            return message_id

    async def get_conversation_history(
        self,
        user: User,
        conversation_id: UUID,
        limit: int = 50,
    ) -> list[dict]:
        """Get conversation history for a user."""
        query = """
            SELECT pk, sender_pk, message, is_overlord, response_to, created_at
            FROM overlord_chat_messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            LIMIT $2
        """

        results = await self.db.fetch(query, conversation_id, limit)

        return [
            {
                "id": str(row["pk"]),
                "sender_id": str(row["sender_pk"]) if row["sender_pk"] else None,
                "message": row["message"],
                "is_overlord": row["is_overlord"],
                "response_to": str(row["response_to"]) if row["response_to"] else None,
                "timestamp": row["created_at"].isoformat(),
            }
            for row in results
        ]

    async def get_user_conversations(self, user: User, limit: int = 10) -> list[dict]:
        """Get list of user's conversations."""
        query = """
            SELECT DISTINCT conversation_id, MAX(created_at) as last_message_at
            FROM overlord_chat_messages
            WHERE sender_pk = $1 OR (sender_pk IS NULL AND conversation_id IN (
                SELECT DISTINCT conversation_id FROM overlord_chat_messages WHERE sender_pk = $1
            ))
            GROUP BY conversation_id
            ORDER BY last_message_at DESC
            LIMIT $2
        """

        results = await self.db.fetch(query, user.pk, limit)

        conversations = []
        for row in results:
            # Get the last message for preview
            last_msg_query = """
                SELECT message, is_overlord
                FROM overlord_chat_messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            last_msg = await self.db.fetchrow(last_msg_query, row["conversation_id"])

            conversations.append(
                {
                    "conversation_id": str(row["conversation_id"]),
                    "last_message_at": row["last_message_at"].isoformat(),
                    "last_message": last_msg["message"] if last_msg else "",
                    "last_message_from_overlord": last_msg["is_overlord"]
                    if last_msg
                    else False,
                }
            )

        return conversations
