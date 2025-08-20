"""Comprehensive tests for private message repository."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.private_message import ConversationSummary
from therobotoverlord_api.database.models.private_message import MessageSearchResult
from therobotoverlord_api.database.models.private_message import MessageThread
from therobotoverlord_api.database.models.private_message import PrivateMessageCreate
from therobotoverlord_api.database.models.private_message import (
    PrivateMessageWithParticipants,
)
from therobotoverlord_api.database.models.private_message import UnreadMessageCount
from therobotoverlord_api.database.repositories.private_message import (
    PrivateMessageRepository,
)


@pytest.fixture
def mock_connection():
    """Create a mock database connection."""
    return AsyncMock()


@pytest.fixture
def repository():
    """Create PrivateMessageRepository instance."""
    return PrivateMessageRepository()


@pytest.fixture
def sample_user_pks():
    """Sample user primary keys for testing."""
    return {"user1": uuid4(), "user2": uuid4(), "user3": uuid4()}


@pytest.fixture
def sample_message_create(sample_user_pks):
    """Create sample PrivateMessageCreate data."""
    return PrivateMessageCreate(
        sender_pk=sample_user_pks["user1"],
        recipient_pk=sample_user_pks["user2"],
        content="Test message content.",
    )


class TestConversationIdGeneration:
    """Test conversation ID generation logic."""

    def test_generate_conversation_id_consistent_order(self, repository):
        """Test that conversation ID is consistent regardless of user order."""
        user1, user2 = uuid4(), uuid4()

        id1 = repository._generate_conversation_id(user1, user2)
        id2 = repository._generate_conversation_id(user2, user1)

        assert id1 == id2
        assert id1.startswith("users_")

    def test_generate_conversation_id_format(self, repository):
        """Test conversation ID format."""
        user1, user2 = uuid4(), uuid4()
        conv_id = repository._generate_conversation_id(user1, user2)

        parts = conv_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "users"
        assert parts[1] == str(min(user1, user2))
        assert parts[2] == str(max(user1, user2))


class TestCreateMessage:
    """Test message creation functionality."""

    @pytest.mark.asyncio
    async def test_create_message_success(
        self, repository, sample_message_create, mock_connection
    ):
        """Test successful message creation."""
        expected_pk = uuid4()
        mock_record = {
            "pk": expected_pk,
            "sender_pk": sample_message_create.sender_pk,
            "recipient_pk": sample_message_create.recipient_pk,
            "content": sample_message_create.content,
            "sent_at": datetime.now(UTC),
            "status": ContentStatus.SUBMITTED,
            "conversation_id": f"users_{min(sample_message_create.sender_pk, sample_message_create.recipient_pk)}_{max(sample_message_create.sender_pk, sample_message_create.recipient_pk)}",
            "read_at": None,
            "moderated_at": None,
            "moderator_feedback": None,
        }

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await repository.create_message(sample_message_create)

            assert result is not None
            assert result.pk == expected_pk
            assert result.status == ContentStatus.SUBMITTED
            mock_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_message_missing_sender(
        self, repository, sample_message_create
    ):
        """Test message creation with missing sender."""
        sample_message_create.sender_pk = None
        result = await repository.create_message(sample_message_create)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_message_database_error(
        self, repository, sample_message_create, mock_connection
    ):
        """Test message creation with database error."""
        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.side_effect = Exception("Database error")

            result = await repository.create_message(sample_message_create)
            assert result is None


class TestGetConversation:
    """Test conversation retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_conversation_success(
        self, repository, sample_user_pks, mock_connection
    ):
        """Test successful conversation retrieval."""
        user1_pk, user2_pk = sample_user_pks["user1"], sample_user_pks["user2"]

        mock_messages = [
            {
                "pk": uuid4(),
                "sender_pk": user1_pk,
                "sender_username": "user1",
                "sender_display_name": "User One",
                "recipient_pk": user2_pk,
                "recipient_username": "user2",
                "recipient_display_name": "User Two",
                "content": "Hello there",
                "sent_at": datetime.now(UTC),
                "status": ContentStatus.APPROVED,
                "conversation_id": f"users_{min(user1_pk, user2_pk)}_{max(user1_pk, user2_pk)}",
                "read_at": None,
                "moderated_at": None,
                "moderator_feedback": None,
            }
        ]

        mock_other_user = {"username": "user2", "display_name": "User Two"}

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.return_value = mock_messages
            mock_connection.fetchval.return_value = 1
            mock_connection.fetchrow.return_value = mock_other_user

            result = await repository.get_conversation(user1_pk, user2_pk)

            assert result is not None
            assert isinstance(result, MessageThread)
            assert len(result.messages) == 1
            assert result.total_count == 1

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(
        self, repository, sample_user_pks, mock_connection
    ):
        """Test conversation retrieval when other user not found."""
        user1_pk, user2_pk = sample_user_pks["user1"], sample_user_pks["user2"]

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.return_value = []
            mock_connection.fetchval.return_value = 0
            mock_connection.fetchrow.return_value = None

            result = await repository.get_conversation(user1_pk, user2_pk)
            assert result is None


class TestGetUserConversations:
    """Test user conversations listing functionality."""

    @pytest.mark.asyncio
    async def test_get_user_conversations_success(
        self, repository, sample_user_pks, mock_connection
    ):
        """Test successful user conversations retrieval."""
        user_pk = sample_user_pks["user1"]
        other_user_pk = sample_user_pks["user2"]

        mock_conversations = [
            {
                "conversation_id": f"users_{min(user_pk, other_user_pk)}_{max(user_pk, other_user_pk)}",
                "other_user_pk": other_user_pk,
                "other_user_username": "user2",
                "other_user_display_name": "User Two",
                "last_message_content": "Hello there",
                "last_message_sent_at": datetime.now(UTC),
                "last_message_sender_pk": other_user_pk,
                "unread_count": 2,
                "total_messages": 5,
            }
        ]

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.return_value = mock_conversations

            result = await repository.get_user_conversations(user_pk)

            assert len(result) == 1
            assert isinstance(result[0], ConversationSummary)
            assert result[0].other_user_username == "user2"

    @pytest.mark.asyncio
    async def test_get_user_conversations_database_error(
        self, repository, sample_user_pks, mock_connection
    ):
        """Test user conversations with database error."""
        user_pk = sample_user_pks["user1"]

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.side_effect = Exception("Database error")

            result = await repository.get_user_conversations(user_pk)
            assert result == []


class TestMarkAsRead:
    """Test message read status functionality."""

    @pytest.mark.asyncio
    async def test_mark_message_as_read_success(self, repository, mock_connection):
        """Test successful message marking as read."""
        message_id, user_pk = uuid4(), uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.execute.return_value = "UPDATE 1"

            result = await repository.mark_as_read(message_id, user_pk)
            assert result is True

    @pytest.mark.asyncio
    async def test_mark_conversation_as_read_success(
        self, repository, sample_user_pks, mock_connection
    ):
        """Test successful conversation marking as read."""
        user1_pk, user2_pk = sample_user_pks["user1"], sample_user_pks["user2"]

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.execute.return_value = "UPDATE 3"

            result = await repository.mark_conversation_as_read(user1_pk, user2_pk)
            assert result == 3


class TestUnreadCount:
    """Test unread message count functionality."""

    @pytest.mark.asyncio
    async def test_get_unread_count_success(self, repository, mock_connection):
        """Test successful unread count retrieval."""
        user_pk = uuid4()
        mock_record = {"total_unread": 5, "conversations_with_unread": 2}

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await repository.get_unread_count(user_pk)

            assert isinstance(result, UnreadMessageCount)
            assert result.total_unread == 5
            assert result.conversations_with_unread == 2

    @pytest.mark.asyncio
    async def test_get_unread_count_database_error(self, repository, mock_connection):
        """Test unread count with database error."""
        user_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.side_effect = Exception("Database error")

            result = await repository.get_unread_count(user_pk)

            assert isinstance(result, UnreadMessageCount)
            assert result.total_unread == 0


class TestSearchMessages:
    """Test message search functionality."""

    @pytest.mark.asyncio
    async def test_search_messages_success(
        self, repository, sample_user_pks, mock_connection
    ):
        """Test successful message search."""
        user_pk, other_user_pk = sample_user_pks["user1"], sample_user_pks["user2"]

        mock_records = [
            {
                "pk": uuid4(),
                "sender_pk": user_pk,
                "sender_username": "user1",
                "sender_display_name": "User One",
                "recipient_pk": other_user_pk,
                "recipient_username": "user2",
                "recipient_display_name": "User Two",
                "content": "Hello world",
                "sent_at": datetime.now(UTC),
                "status": ContentStatus.APPROVED,
                "conversation_id": f"users_{min(user_pk, other_user_pk)}_{max(user_pk, other_user_pk)}",
                "read_at": None,
                "moderated_at": None,
                "moderator_feedback": None,
                "match_snippet": "<b>Hello</b> world",
            }
        ]

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.return_value = mock_records

            result = await repository.search_messages(user_pk, "hello")

            assert len(result) == 1
            assert isinstance(result[0], MessageSearchResult)
            assert result[0].message.content == "Hello world"


class TestModerationMethods:
    """Test message moderation functionality."""

    @pytest.mark.asyncio
    async def test_approve_message_success(self, repository, mock_connection):
        """Test successful message approval."""
        message_id = uuid4()
        mock_record = {
            "pk": message_id,
            "sender_pk": uuid4(),
            "recipient_pk": uuid4(),
            "content": "Test content",
            "sent_at": datetime.now(UTC),
            "status": ContentStatus.APPROVED,
            "conversation_id": "users_123_456",
            "read_at": None,
            "moderated_at": datetime.now(UTC),
            "moderator_feedback": "Approved",
        }

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await repository.approve_message(message_id, "Approved")

            assert result is not None
            assert result.status == ContentStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject_message_success(self, repository, mock_connection):
        """Test successful message rejection."""
        message_id = uuid4()
        mock_record = {
            "pk": message_id,
            "sender_pk": uuid4(),
            "recipient_pk": uuid4(),
            "content": "Test content",
            "sent_at": datetime.now(UTC),
            "status": ContentStatus.REJECTED,
            "conversation_id": "users_123_456",
            "read_at": None,
            "moderated_at": datetime.now(UTC),
            "moderator_feedback": "Inappropriate",
        }

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await repository.reject_message(message_id, "Inappropriate")

            assert result is not None
            assert result.status == ContentStatus.REJECTED

    @pytest.mark.asyncio
    async def test_get_messages_for_moderation_success(
        self, repository, mock_connection
    ):
        """Test getting messages for moderation."""
        mock_records = [
            {
                "pk": uuid4(),
                "sender_pk": uuid4(),
                "sender_username": "user1",
                "sender_display_name": "User One",
                "recipient_pk": uuid4(),
                "recipient_username": "user2",
                "recipient_display_name": "User Two",
                "content": "Pending message",
                "sent_at": datetime.now(UTC),
                "status": ContentStatus.SUBMITTED,
                "conversation_id": "users_123_456",
                "read_at": None,
                "moderated_at": None,
                "moderator_feedback": None,
            }
        ]

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.return_value = mock_records

            result = await repository.get_messages_for_moderation()

            assert len(result) == 1
            assert isinstance(result[0], PrivateMessageWithParticipants)
            assert result[0].status == ContentStatus.SUBMITTED


class TestDeleteMessage:
    """Test message deletion functionality."""

    @pytest.mark.asyncio
    async def test_delete_message_by_sender(self, repository, mock_connection):
        """Test message deletion by sender."""
        message_id, user_pk = uuid4(), uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.execute.return_value = "UPDATE 1"

            result = await repository.delete_message(message_id, user_pk)
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_message_by_admin(self, repository, mock_connection):
        """Test message deletion by admin."""
        message_id, user_pk = uuid4(), uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.execute.return_value = "UPDATE 1"

            result = await repository.delete_message(message_id, user_pk, is_admin=True)
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_message_not_found(self, repository, mock_connection):
        """Test deleting non-existent message."""
        message_id, user_pk = uuid4(), uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.private_message.get_db_connection"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_connection
            mock_connection.execute.return_value = "UPDATE 0"

            result = await repository.delete_message(message_id, user_pk)
            assert result is False
