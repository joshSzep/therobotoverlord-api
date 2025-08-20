"""Comprehensive unit tests for Private Messages API endpoints."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.messages import router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.private_message import ConversationSummary
from therobotoverlord_api.database.models.private_message import MessageSearchResult
from therobotoverlord_api.database.models.private_message import MessageThread
from therobotoverlord_api.database.models.private_message import PrivateMessage
from therobotoverlord_api.database.models.private_message import (
    PrivateMessageWithParticipants,
)
from therobotoverlord_api.database.models.private_message import UnreadMessageCount
from therobotoverlord_api.database.models.user import User


@pytest.fixture
def test_app():
    """Create test FastAPI app with messages router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    return User(
        pk=uuid4(),
        email="test@example.com",
        google_id="google123",
        username="testuser",
        role=UserRole.CITIZEN,
        is_banned=False,
        is_sanctioned=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_admin_user():
    """Mock admin user for testing."""
    return User(
        pk=uuid4(),
        email="admin@example.com",
        google_id="admin123",
        username="adminuser",
        role=UserRole.ADMIN,
        is_banned=False,
        is_sanctioned=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_moderator_user():
    """Mock moderator user for testing."""
    return User(
        pk=uuid4(),
        email="moderator@example.com",
        google_id="mod123",
        username="moderator",
        role=UserRole.MODERATOR,
        is_banned=False,
        is_sanctioned=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_banned_user():
    """Mock banned user for testing."""
    return User(
        pk=uuid4(),
        email="banned@example.com",
        google_id="banned123",
        username="banneduser",
        role=UserRole.CITIZEN,
        is_banned=True,
        is_sanctioned=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_sanctioned_user():
    """Mock sanctioned user for testing."""
    return User(
        pk=uuid4(),
        email="sanctioned@example.com",
        google_id="sanctioned123",
        username="sanctioneduser",
        role=UserRole.CITIZEN,
        is_banned=False,
        is_sanctioned=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestSendMessage:
    """Test cases for POST /messages/ endpoint."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, client, test_app, mock_user):
        """Test successful message sending."""
        recipient_id = uuid4()
        message_data = {
            "recipient_pk": str(recipient_id),
            "content": "Hello, this is a test message",
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        created_message = PrivateMessage(
            pk=uuid4(),
            sender_pk=mock_user.pk,
            recipient_pk=recipient_id,
            content="Hello, this is a test message",
            sent_at=datetime.now(UTC),
            status=ContentStatus.SUBMITTED,
            conversation_id=f"users_{min(mock_user.pk, recipient_id)}_{max(mock_user.pk, recipient_id)}",
        )

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.create_message.return_value = created_message
            mock_repo_class.return_value = mock_repo

            with patch(
                "therobotoverlord_api.api.messages.get_queue_service"
            ) as mock_queue_service:
                mock_service = AsyncMock()
                mock_service.add_message_to_queue.return_value = "queue123"
                mock_queue_service.return_value = mock_service

                response = client.post("/messages/", json=message_data)

                assert response.status_code == status.HTTP_201_CREATED
                response_data = response.json()
                assert response_data["content"] == "Hello, this is a test message"
                assert response_data["sender_pk"] == str(mock_user.pk)
                assert response_data["recipient_pk"] == str(recipient_id)

    @pytest.mark.asyncio
    async def test_send_message_banned_user(self, client, test_app, mock_banned_user):
        """Test banned user cannot send messages."""
        message_data = {
            "recipient_pk": str(uuid4()),
            "content": "Hello, this is a test message",
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_banned_user

        response = client.post("/messages/", json=message_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Banned users cannot send messages" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_send_message_sanctioned_user(
        self, client, test_app, mock_sanctioned_user
    ):
        """Test sanctioned user cannot send messages."""
        message_data = {
            "recipient_pk": str(uuid4()),
            "content": "Hello, this is a test message",
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_sanctioned_user

        response = client.post("/messages/", json=message_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Sanctioned users cannot send messages" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_send_message_to_self(self, client, test_app, mock_user):
        """Test sending message to self (should fail)."""
        message_data = {
            "recipient_pk": str(mock_user.pk),
            "content": "Hello, this is a test message",
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.post("/messages/", json=message_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot send message to yourself" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_send_message_creation_fails(self, client, test_app, mock_user):
        """Test handling when message creation fails."""
        message_data = {
            "recipient_pk": str(uuid4()),
            "content": "Hello, this is a test message",
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.create_message.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.post("/messages/", json=message_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to create message" in response.json()["detail"]


class TestGetConversations:
    """Test cases for GET /messages/conversations endpoint."""

    @pytest.mark.asyncio
    async def test_get_conversations_success(self, client, test_app, mock_user):
        """Test successful retrieval of conversations."""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        other_user1_pk = uuid4()
        other_user2_pk = uuid4()
        conversations = [
            ConversationSummary(
                conversation_id=f"users_{min(mock_user.pk, other_user1_pk)}_{max(mock_user.pk, other_user1_pk)}",
                other_user_pk=other_user1_pk,
                other_user_username="user1",
                other_user_display_name="User One",
                last_message_content="Hello there",
                last_message_sent_at=datetime.now(UTC),
                last_message_sender_pk=other_user1_pk,
                unread_count=2,
                total_messages=5,
            ),
            ConversationSummary(
                conversation_id=f"users_{min(mock_user.pk, other_user2_pk)}_{max(mock_user.pk, other_user2_pk)}",
                other_user_pk=other_user2_pk,
                other_user_username="user2",
                other_user_display_name="User Two",
                last_message_content="How are you?",
                last_message_sent_at=datetime.now(UTC),
                last_message_sender_pk=mock_user.pk,
                unread_count=0,
                total_messages=3,
            ),
        ]

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_user_conversations.return_value = conversations
            mock_repo_class.return_value = mock_repo

            response = client.get("/messages/conversations")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert len(response_data) == 2
            assert response_data[0]["other_user_username"] == "user1"
            assert response_data[0]["unread_count"] == 2

    @pytest.mark.asyncio
    async def test_get_conversations_with_pagination(self, client, test_app, mock_user):
        """Test conversations with pagination parameters."""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_user_conversations.return_value = []
            mock_repo_class.return_value = mock_repo

            response = client.get("/messages/conversations?limit=10&offset=5")

            assert response.status_code == status.HTTP_200_OK
            mock_repo.get_user_conversations.assert_called_once_with(
                mock_user.pk, 10, 5
            )


class TestGetConversation:
    """Test cases for GET /messages/conversations/{other_user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_conversation_success(self, client, test_app, mock_user):
        """Test successful retrieval of specific conversation."""
        other_user_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        conversation = MessageThread(
            conversation_id=f"users_{min(mock_user.pk, other_user_id)}_{max(mock_user.pk, other_user_id)}",
            messages=[
                PrivateMessageWithParticipants(
                    pk=uuid4(),
                    sender_pk=mock_user.pk,
                    sender_username="testuser",
                    sender_display_name="Test User",
                    recipient_pk=other_user_id,
                    recipient_username="otheruser",
                    recipient_display_name="Other User",
                    content="Hello there",
                    sent_at=datetime.now(UTC),
                    status=ContentStatus.APPROVED,
                    conversation_id=f"users_{min(mock_user.pk, other_user_id)}_{max(mock_user.pk, other_user_id)}",
                ),
            ],
            total_count=1,
            has_more=False,
            other_user_pk=other_user_id,
            other_user_username="otheruser",
            other_user_display_name="Other User",
        )

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_conversation.return_value = conversation
            mock_repo_class.return_value = mock_repo

            response = client.get(f"/messages/conversations/{other_user_id}")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["total_count"] == 1
            assert len(response_data["messages"]) == 1

    @pytest.mark.asyncio
    async def test_get_conversation_with_self(self, client, test_app, mock_user):
        """Test trying to get conversation with self."""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.get(f"/messages/conversations/{mock_user.pk}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot view conversation with yourself" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, client, test_app, mock_user):
        """Test conversation not found."""
        other_user_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_conversation.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get(f"/messages/conversations/{other_user_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Conversation not found" in response.json()["detail"]


class TestMarkAsRead:
    """Test cases for marking messages as read."""

    @pytest.mark.asyncio
    async def test_mark_conversation_as_read(self, client, test_app, mock_user):
        """Test marking entire conversation as read."""
        other_user_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.mark_conversation_as_read.return_value = 3
            mock_repo_class.return_value = mock_repo

            response = client.patch(f"/messages/conversations/{other_user_id}/read")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["messages_marked_read"] == 3

    @pytest.mark.asyncio
    async def test_mark_message_as_read(self, client, test_app, mock_user):
        """Test marking specific message as read."""
        message_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.mark_as_read.return_value = True
            mock_repo_class.return_value = mock_repo

            response = client.patch(f"/messages/{message_id}/read")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["marked_as_read"] is True

    @pytest.mark.asyncio
    async def test_mark_message_as_read_not_found(self, client, test_app, mock_user):
        """Test marking non-existent message as read."""
        message_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.mark_as_read.return_value = False
            mock_repo_class.return_value = mock_repo

            response = client.patch(f"/messages/{message_id}/read")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Message not found or already read" in response.json()["detail"]


class TestUnreadCount:
    """Test cases for GET /messages/unread/count endpoint."""

    @pytest.mark.asyncio
    async def test_get_unread_count(self, client, test_app, mock_user):
        """Test getting unread message count."""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        unread_count = UnreadMessageCount(
            total_unread=5,
            conversations_with_unread=2,
        )

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_unread_count.return_value = unread_count
            mock_repo_class.return_value = mock_repo

            response = client.get("/messages/unread/count")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["total_unread"] == 5
            assert response_data["conversations_with_unread"] == 2


class TestSearchMessages:
    """Test cases for GET /messages/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_messages_success(self, client, test_app, mock_user):
        """Test successful message search."""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        recipient_pk = uuid4()
        search_results = [
            MessageSearchResult(
                message=PrivateMessageWithParticipants(
                    pk=uuid4(),
                    sender_pk=mock_user.pk,
                    sender_username="testuser",
                    sender_display_name="Test User",
                    recipient_pk=recipient_pk,
                    recipient_username="testuser2",
                    recipient_display_name="Test User 2",
                    content="Hello world",
                    sent_at=datetime.now(UTC),
                    status=ContentStatus.APPROVED,
                    conversation_id=f"users_{min(mock_user.pk, recipient_pk)}_{max(mock_user.pk, recipient_pk)}",
                ),
                conversation_id=f"users_{min(mock_user.pk, recipient_pk)}_{max(mock_user.pk, recipient_pk)}",
                match_snippet="Hello world",
            ),
        ]

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.search_messages.return_value = search_results
            mock_repo_class.return_value = mock_repo

            response = client.get("/messages/search?q=hello")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert len(response_data) == 1
            assert response_data[0]["message"]["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_search_messages_invalid_query(self, client, test_app, mock_user):
        """Test search with invalid query parameters."""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        # Query too short
        response = client.get("/messages/search?q=a")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Query too long
        long_query = "x" * 101
        response = client.get(f"/messages/search?q={long_query}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteMessage:
    """Test cases for DELETE /messages/{message_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_message_success(self, client, test_app, mock_user):
        """Test successful message deletion."""
        message_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.delete_message.return_value = True
            mock_repo_class.return_value = mock_repo

            response = client.delete(f"/messages/{message_id}")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_message_not_found(self, client, test_app, mock_user):
        """Test deleting non-existent message."""
        message_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.delete_message.return_value = False
            mock_repo_class.return_value = mock_repo

            response = client.delete(f"/messages/{message_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert (
                "Message not found or you don't have permission"
                in response.json()["detail"]
            )


class TestModerationEndpoints:
    """Test cases for moderation endpoints."""

    @pytest.mark.asyncio
    async def test_get_pending_messages(self, client, test_app, mock_moderator_user):
        """Test getting pending messages for moderation."""
        test_app.dependency_overrides[get_current_user] = lambda: mock_moderator_user

        sender_pk = uuid4()
        recipient_pk = uuid4()
        pending_messages = [
            PrivateMessageWithParticipants(
                pk=uuid4(),
                sender_pk=sender_pk,
                sender_username="sender1",
                sender_display_name="Sender One",
                recipient_pk=recipient_pk,
                recipient_username="recipient1",
                recipient_display_name="Recipient One",
                content="Message pending moderation",
                sent_at=datetime.now(UTC),
                status=ContentStatus.PENDING,
                conversation_id=f"users_{min(sender_pk, recipient_pk)}_{max(sender_pk, recipient_pk)}",
            ),
        ]

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_messages_for_moderation.return_value = pending_messages
            mock_repo_class.return_value = mock_repo

            response = client.get("/messages/pending/list")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert len(response_data) == 1
            assert response_data[0]["content"] == "Message pending moderation"

    @pytest.mark.asyncio
    async def test_approve_message(self, client, test_app, mock_moderator_user):
        """Test approving a message."""
        message_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_moderator_user

        sender_pk = uuid4()
        recipient_pk = uuid4()
        approved_message = PrivateMessage(
            pk=message_id,
            sender_pk=sender_pk,
            recipient_pk=recipient_pk,
            content="Approved message",
            sent_at=datetime.now(UTC),
            status=ContentStatus.APPROVED,
            conversation_id=f"users_{min(sender_pk, recipient_pk)}_{max(sender_pk, recipient_pk)}",
        )

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.approve_message.return_value = approved_message
            mock_repo_class.return_value = mock_repo

            response = client.patch(f"/messages/{message_id}/approve")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["status"] == ContentStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject_message(self, client, test_app, mock_moderator_user):
        """Test rejecting a message."""
        message_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_moderator_user

        sender_pk = uuid4()
        recipient_pk = uuid4()
        rejected_message = PrivateMessage(
            pk=message_id,
            sender_pk=sender_pk,
            recipient_pk=recipient_pk,
            content="Rejected message",
            sent_at=datetime.now(UTC),
            status=ContentStatus.REJECTED,
            conversation_id=f"users_{min(sender_pk, recipient_pk)}_{max(sender_pk, recipient_pk)}",
        )

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.reject_message.return_value = rejected_message
            mock_repo_class.return_value = mock_repo

            response = client.patch(
                f"/messages/{message_id}/reject?overlord_feedback=Inappropriate content"
            )

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["status"] == ContentStatus.REJECTED

    @pytest.mark.asyncio
    async def test_non_moderator_access_pending(self, client, test_app, mock_user):
        """Test non-moderator trying to access pending messages."""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.get("/messages/pending/list")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAdminEndpoints:
    """Test cases for admin-only endpoints."""

    @pytest.mark.asyncio
    async def test_admin_view_conversation(self, client, test_app, mock_admin_user):
        """Test admin viewing any conversation."""
        user1_id = uuid4()
        user2_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        conversation = MessageThread(
            conversation_id=f"users_{min(user1_id, user2_id)}_{max(user1_id, user2_id)}",
            messages=[
                PrivateMessageWithParticipants(
                    pk=uuid4(),
                    sender_pk=user1_id,
                    sender_username="user1",
                    sender_display_name="User One",
                    recipient_pk=user2_id,
                    recipient_username="user2",
                    recipient_display_name="User Two",
                    content="Admin can see this",
                    sent_at=datetime.now(UTC),
                    status=ContentStatus.APPROVED,
                    conversation_id=f"users_{min(user1_id, user2_id)}_{max(user1_id, user2_id)}",
                ),
            ],
            total_count=1,
            has_more=False,
            other_user_pk=user2_id,
            other_user_username="user2",
            other_user_display_name="User Two",
        )

        with patch(
            "therobotoverlord_api.api.messages.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_conversation.return_value = conversation
            mock_repo_class.return_value = mock_repo

            response = client.get(
                f"/messages/admin/conversations/{user1_id}/{user2_id}"
            )

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["total_count"] == 1

    @pytest.mark.asyncio
    async def test_admin_view_same_user_conversation(
        self, client, test_app, mock_admin_user
    ):
        """Test admin trying to view conversation between same user."""
        user_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        response = client.get(f"/messages/admin/conversations/{user_id}/{user_id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot view conversation between same user" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_non_admin_access_admin_endpoint(self, client, test_app, mock_user):
        """Test non-admin trying to access admin endpoint."""
        user1_id = uuid4()
        user2_id = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.get(f"/messages/admin/conversations/{user1_id}/{user2_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN
