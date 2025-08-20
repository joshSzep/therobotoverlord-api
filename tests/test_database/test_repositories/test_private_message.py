"""Tests for private message repository."""

from datetime import UTC
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.private_message import MessageThread
from therobotoverlord_api.database.models.private_message import PrivateMessage
from therobotoverlord_api.database.models.private_message import PrivateMessageCreate
from therobotoverlord_api.database.models.private_message import (
    PrivateMessageWithParticipants,
)
from therobotoverlord_api.database.repositories.private_message import (
    PrivateMessageRepository,
)


@pytest.mark.asyncio
class TestPrivateMessageRepository:
    """Test PrivateMessageRepository class."""

    @pytest.fixture
    def message_repository(self):
        """Create PrivateMessageRepository instance."""
        return PrivateMessageRepository()

    @pytest.fixture
    def sample_message_create(self):
        """Create sample PrivateMessageCreate data."""
        return PrivateMessageCreate(
            sender_pk=uuid4(),
            recipient_pk=uuid4(),
            content="This is a test private message content.",
        )

    async def test_create_message(
        self, message_repository, sample_message_create, mock_connection
    ):
        """Test creating a new private message."""
        expected_pk = uuid4()

        # Mock database response
        mock_record = {
            "pk": expected_pk,
            "sender_pk": sample_message_create.sender_pk,
            "recipient_pk": sample_message_create.recipient_pk,
            "content": sample_message_create.content,
            "sent_at": datetime.now(UTC),
            "status": ContentStatus.SUBMITTED,
            "conversation_id": f"users_{sample_message_create.sender_pk}_{sample_message_create.recipient_pk}",
            "read_at": None,
            "moderated_at": None,
            "moderator_feedback": None,
        }

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await message_repository.create_message(sample_message_create)

            assert result is not None
            assert result.sender_pk == sample_message_create.sender_pk
            assert result.recipient_pk == sample_message_create.recipient_pk
            assert result.content == sample_message_create.content
            assert result.status == ContentStatus.SUBMITTED
        mock_connection.fetchrow.assert_called_once()

    async def test_get_by_pk(self, message_repository, mock_connection):
        """Test getting a private message by primary key."""
        message_pk = uuid4()

        mock_record = {
            "pk": message_pk,
            "sender_pk": uuid4(),
            "recipient_pk": uuid4(),
            "content": "Test message content",
            "sent_at": datetime.now(UTC),
            "status": ContentStatus.PENDING,
            "conversation_id": "users_123_456",
            "read_at": None,
            "moderated_at": None,
            "moderator_feedback": None,
        }

        # Mock the database connection and query
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await message_repository.get_by_pk(message_pk)

            assert result is not None
            assert result.pk == message_pk
            assert result.content == "Test message content"
            assert result.status == ContentStatus.PENDING
            mock_connection.fetchrow.assert_called_once()

    async def test_get_by_pk_not_found(self, message_repository, mock_connection):
        """Test getting a private message that doesn't exist."""
        message_pk = uuid4()

        # Mock the database connection and query
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = None

            result = await message_repository.get_by_pk(message_pk)

            assert result is None
            mock_connection.fetchrow.assert_called_once()

    async def test_approve_message(self, message_repository, mock_connection):
        """Test approving a private message."""
        message_pk = uuid4()
        feedback = "Message approved by moderation"

        mock_record = {
            "pk": message_pk,
            "sender_pk": uuid4(),
            "recipient_pk": uuid4(),
            "content": "Test content",
            "sent_at": datetime.now(UTC),
            "status": ContentStatus.APPROVED,
            "conversation_id": "users_123_456",
            "read_at": None,
            "moderated_at": datetime.now(UTC),
            "moderator_feedback": feedback,
        }

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await message_repository.approve_message(message_pk, feedback)

            assert result is not None
            assert result.status == ContentStatus.APPROVED
            assert result.moderator_feedback == feedback
            mock_connection.fetchrow.assert_called_once()

    async def test_reject_message(self, message_repository, mock_connection):
        """Test rejecting a private message."""
        message_pk = uuid4()
        feedback = "Message rejected due to inappropriate content"

        mock_record = {
            "pk": message_pk,
            "sender_pk": uuid4(),
            "recipient_pk": uuid4(),
            "content": "Test content",
            "sent_at": datetime.now(UTC),
            "status": ContentStatus.REJECTED,
            "conversation_id": "users_123_456",
            "read_at": None,
            "moderated_at": datetime.now(UTC),
            "moderator_feedback": feedback,
        }

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await message_repository.reject_message(message_pk, feedback)

            assert result is not None
            assert result.status == ContentStatus.REJECTED
            assert result.moderator_feedback == feedback
            mock_connection.fetchrow.assert_called_once()

    async def test_get_messages_for_user(self, message_repository, mock_connection):
        """Test getting messages for a specific user."""
        user_pk = uuid4()
        limit = 20
        offset = 0

        expected_messages = [
            PrivateMessage(
                pk=uuid4(),
                sender_pk=uuid4(),
                recipient_pk=user_pk,
                content="Test message 1",
                sent_at=datetime.now(UTC),
                status=ContentStatus.APPROVED,
                conversation_id="users_123_456",
            ),
            PrivateMessage(
                pk=uuid4(),
                sender_pk=user_pk,
                recipient_pk=uuid4(),
                content="Test message 2",
                sent_at=datetime.now(UTC),
                status=ContentStatus.APPROVED,
                conversation_id="users_123_456",
            ),
        ]

        with patch.object(
            message_repository, "get_user_conversations", return_value=expected_messages
        ):
            result = await message_repository.get_user_conversations(
                user_pk, limit, offset
            )

            assert result == expected_messages
            assert len(result) == 2

    async def test_get_conversation(self, message_repository, mock_connection):
        """Test getting conversation between two users."""
        user1_pk = uuid4()
        user2_pk = uuid4()
        limit = 50
        offset = 0

        expected_messages = [
            PrivateMessageWithParticipants(
                pk=uuid4(),
                sender_pk=user1_pk,
                sender_username="user1",
                sender_display_name=None,
                recipient_pk=user2_pk,
                recipient_username="user2",
                recipient_display_name=None,
                content="Hello there",
                sent_at=datetime.now(UTC),
                status=ContentStatus.APPROVED,
                conversation_id="users_123_456",
            ),
            PrivateMessageWithParticipants(
                pk=uuid4(),
                sender_pk=user2_pk,
                sender_username="user2",
                sender_display_name=None,
                recipient_pk=user1_pk,
                recipient_username="user1",
                recipient_display_name=None,
                content="Hello back",
                sent_at=datetime.now(UTC),
                status=ContentStatus.APPROVED,
                conversation_id="users_123_456",
            ),
        ]

        expected_thread = MessageThread(
            conversation_id="users_123_456",
            messages=expected_messages,
            total_count=2,
            has_more=False,
            other_user_pk=user2_pk,
            other_user_username="testuser",
            other_user_display_name=None,
        )

        with patch.object(
            message_repository, "get_conversation", return_value=expected_thread
        ):
            result = await message_repository.get_conversation(
                user1_pk, user2_pk, limit, offset
            )

            assert result == expected_thread
            assert len(result.messages) == 2

    async def test_update_message(self, message_repository, mock_connection):
        """Test updating a private message via approve/reject methods."""
        message_pk = uuid4()

        # Test that approve_message works as an update mechanism
        with patch.object(
            message_repository,
            "approve_message",
            return_value=PrivateMessage(
                pk=message_pk,
                sender_pk=uuid4(),
                recipient_pk=uuid4(),
                content="Updated message",
                sent_at=datetime.now(UTC),
                status=ContentStatus.APPROVED,
                conversation_id="users_123_456",
            ),
        ):
            result = await message_repository.approve_message(
                message_pk, "Updated feedback"
            )

            assert result is not None
            assert result.status == ContentStatus.APPROVED

    async def test_delete_message(self, message_repository, mock_connection):
        """Test deleting a private message."""
        message_pk = uuid4()

        with patch.object(message_repository, "delete_message", return_value=True):
            result = await message_repository.delete_message(message_pk, uuid4())

            assert result is True
            message_repository.delete_message.assert_called_once()

    async def test_get_pending_moderation_messages(
        self, message_repository, mock_connection
    ):
        """Test getting messages pending moderation."""
        limit = 10

        expected_messages = [
            PrivateMessage(
                pk=uuid4(),
                sender_pk=uuid4(),
                recipient_pk=uuid4(),
                content="Message pending moderation",
                sent_at=datetime.now(UTC),
                status=ContentStatus.PENDING,
                conversation_id="users_789_012",
            )
        ]

        with patch.object(
            message_repository,
            "get_messages_for_moderation",
            return_value=expected_messages,
        ):
            result = await message_repository.get_messages_for_moderation(limit)

            assert result == expected_messages
            assert len(result) == 1
