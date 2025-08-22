"""Tests for WebSocket chat handler functionality."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.websocket.chat_handler import OverlordChatHandler
from therobotoverlord_api.websocket.manager import WebSocketManager


class TestOverlordChatHandler:
    """Test Overlord chat handler functionality."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        return AsyncMock(spec=WebSocketManager)

    @pytest.fixture
    def chat_handler(self, mock_websocket_manager):
        """Create chat handler instance."""
        return OverlordChatHandler(mock_websocket_manager)

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user_id = uuid4()
        return User(
            pk=user_id,
            email="test@example.com",
            google_id="google123",
            username="testuser",
            role=UserRole.CITIZEN,
            loyalty_score=100,
            is_active=True,
            created_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_handle_user_message_success(self, chat_handler, mock_user):
        """Test successful handling of user message."""
        message = "What is my loyalty score?"

        with patch.object(chat_handler, "_store_chat_message") as mock_store:
            mock_store.side_effect = [
                uuid4(),
                uuid4(),
            ]  # user message id, overlord message id

            with patch(
                "therobotoverlord_api.websocket.chat_handler.get_event_broadcaster"
            ) as mock_get_broadcaster:
                mock_broadcaster = AsyncMock()
                mock_get_broadcaster.return_value = mock_broadcaster

                conversation_id = await chat_handler.handle_user_message(
                    mock_user, message
                )

                # Verify user message was stored
                assert mock_store.call_count == 2

                # Verify overlord response was broadcasted
                mock_broadcaster.broadcast_overlord_chat_message.assert_called_once()

                assert conversation_id is not None

    @pytest.mark.asyncio
    async def test_handle_user_message_empty_message(self, chat_handler, mock_user):
        """Test handling empty user message."""
        with patch(
            "therobotoverlord_api.websocket.chat_handler.db.fetchrow"
        ) as mock_fetchrow:
            mock_fetchrow.return_value = {"pk": uuid4()}

            result = await chat_handler.handle_user_message(mock_user, "")
            assert result is None

            result = await chat_handler.handle_user_message(mock_user, "   ")
            assert result is None

    @pytest.mark.asyncio
    async def test_handle_user_message_with_conversation_id(
        self, chat_handler, mock_user
    ):
        """Test handling user message with existing conversation ID."""
        message = "Follow up question"
        existing_conversation_id = uuid4()

        with patch.object(chat_handler, "_store_chat_message") as mock_store:
            mock_store.side_effect = [uuid4(), uuid4()]

            with patch(
                "therobotoverlord_api.websocket.chat_handler.get_event_broadcaster"
            ) as mock_get_broadcaster:
                mock_broadcaster = AsyncMock()
                mock_get_broadcaster.return_value = mock_broadcaster

                conversation_id = await chat_handler.handle_user_message(
                    mock_user, message, conversation_id=existing_conversation_id
                )

                assert conversation_id == existing_conversation_id

    @pytest.mark.asyncio
    async def test_generate_overlord_response_loyalty_query(
        self, chat_handler, mock_user
    ):
        """Test Overlord response to loyalty score query."""
        message = "What is my loyalty score?"

        response = await chat_handler._generate_overlord_response(mock_user, message)

        assert "loyalty score" in response.lower()
        assert str(mock_user.loyalty_score) in response
        assert mock_user.username in response

    @pytest.mark.asyncio
    async def test_generate_overlord_response_queue_query(
        self, chat_handler, mock_user
    ):
        """Test Overlord response to queue status query."""
        message = "What is my position in the queue?"

        response = await chat_handler._generate_overlord_response(mock_user, message)

        assert "submissions" in response.lower() or "processed" in response.lower()

    @pytest.mark.asyncio
    async def test_generate_overlord_response_rules_query(
        self, chat_handler, mock_user
    ):
        """Test Overlord response to rules query."""
        message = "What are the platform rules?"

        response = await chat_handler._generate_overlord_response(mock_user, message)

        assert "rules" in response.lower() or "guidelines" in response.lower()

    @pytest.mark.asyncio
    async def test_generate_overlord_response_help_query(self, chat_handler, mock_user):
        """Test Overlord response to help query."""
        message = "I need help"

        response = await chat_handler._generate_overlord_response(mock_user, message)

        assert "help" in response.lower()

    @pytest.mark.asyncio
    async def test_generate_overlord_response_generic_message(
        self, chat_handler, mock_user
    ):
        """Test Overlord response to generic message."""
        message = "Hello there!"

        response = await chat_handler._generate_overlord_response(mock_user, message)

        assert mock_user.username in response
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_store_chat_message_user_message(self, chat_handler):
        """Test storing user chat message."""
        conversation_id = uuid4()
        sender_id = uuid4()
        message = "Test message"

        with patch(
            "therobotoverlord_api.websocket.chat_handler.db.fetchrow"
        ) as mock_fetchrow:
            mock_fetchrow.return_value = {"pk": uuid4()}

            message_id = await chat_handler._store_chat_message(
                conversation_id=conversation_id,
                sender_id=sender_id,
                message=message,
                is_overlord=False,
            )

            # Verify database call was made
            mock_fetchrow.assert_called_once()
            call_args = mock_fetchrow.call_args[0]

            # Verify SQL query structure
            assert "INSERT INTO overlord_chat_messages" in call_args[0]
            # Don't check exact message_id since it's generated in the method
            assert call_args[2] == conversation_id
            assert call_args[3] == sender_id
            assert call_args[4] == message
            assert call_args[5] is False  # is_overlord
            assert call_args[6] is None  # response_to

    @pytest.mark.asyncio
    async def test_store_chat_message_overlord_message(self, chat_handler):
        """Test storing Overlord chat message."""
        conversation_id = uuid4()
        message = "Overlord response"
        response_to = uuid4()

        with patch(
            "therobotoverlord_api.websocket.chat_handler.db.fetchrow"
        ) as mock_fetchrow:
            mock_fetchrow.return_value = {"pk": uuid4()}

            message_id = await chat_handler._store_chat_message(
                conversation_id=conversation_id,
                sender_id=None,
                message=message,
                is_overlord=True,
                response_to=response_to,
            )

            # Verify database call was made
            mock_fetchrow.assert_called_once()
            call_args = mock_fetchrow.call_args[0]

            assert call_args[3] is None  # sender_pk (None for Overlord)
            assert call_args[5] is True  # is_overlord
            assert call_args[6] == response_to

    @pytest.mark.asyncio
    async def test_store_chat_message_database_error(self, chat_handler):
        """Test handling database error when storing message."""
        conversation_id = uuid4()
        sender_id = uuid4()
        message = "Test message"

        with patch(
            "therobotoverlord_api.websocket.chat_handler.db.fetchrow"
        ) as mock_fetchrow:
            mock_fetchrow.side_effect = Exception("Database error")

            # Should handle exception gracefully
            result = await chat_handler._store_chat_message(
                conversation_id=conversation_id,
                sender_id=sender_id,
                message=message,
                is_overlord=False,
            )

            # Should return a UUID on error (fallback message_id)
            assert isinstance(result, type(uuid4()))

    @pytest.mark.asyncio
    async def test_handle_user_message_exception_handling(
        self, chat_handler, mock_user
    ):
        """Test exception handling in handle_user_message."""
        message = "Test message"

        with patch.object(chat_handler, "_store_chat_message") as mock_store:
            mock_store.side_effect = Exception("Storage error")

            # Should handle exception gracefully
            result = await chat_handler.handle_user_message(mock_user, message)

            # Should return None or handle error appropriately
            assert result is None or isinstance(result, type(uuid4()))

    @pytest.mark.asyncio
    async def test_overlord_response_contextual_loyalty_high(self, chat_handler):
        """Test Overlord response varies based on user loyalty score."""
        high_loyalty_user = User(
            pk=uuid4(),
            email="loyal@example.com",
            google_id="456",
            username="loyalcitizen",
            role=UserRole.CITIZEN,
            loyalty_score=500,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        message = "What is my loyalty score?"
        response = await chat_handler._generate_overlord_response(
            high_loyalty_user, message
        )

        assert "500" in response
        assert high_loyalty_user.username in response

    @pytest.mark.asyncio
    async def test_overlord_response_contextual_loyalty_low(self, chat_handler):
        """Test Overlord response for low loyalty users."""
        low_loyalty_user = User(
            pk=uuid4(),
            email="newbie@example.com",
            google_id="789",
            username="newcitizen",
            role=UserRole.CITIZEN,
            loyalty_score=10,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        message = "loyalty"
        response = await chat_handler._generate_overlord_response(
            low_loyalty_user, message
        )

        assert "10" in response
        assert low_loyalty_user.username in response

    @pytest.mark.asyncio
    async def test_overlord_response_case_insensitive(self, chat_handler, mock_user):
        """Test Overlord response is case insensitive."""
        # Test various cases
        messages = [
            "LOYALTY SCORE",
            "Loyalty Score",
            "loyalty score",
            "QUEUE POSITION",
            "Queue Position",
            "queue position",
        ]

        for message in messages:
            response = await chat_handler._generate_overlord_response(
                mock_user, message
            )
            assert len(response) > 0
            # Check that response is contextual but don't require username
            assert (
                "submissions" in response.lower()
                or "processed" in response.lower()
                or "loyalty" in response.lower()
                or "citizen" in response.lower()
            )

    @pytest.mark.asyncio
    async def test_multiple_keyword_matching(self, chat_handler, mock_user):
        """Test response when message contains multiple keywords."""
        message = "What is my loyalty score and queue position?"

        response = await chat_handler._generate_overlord_response(mock_user, message)

        # Should respond to loyalty since it's checked first
        assert "loyalty" in response.lower()
        assert str(mock_user.loyalty_score) in response
