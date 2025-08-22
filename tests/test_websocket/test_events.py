"""Tests for WebSocket event broadcasting."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from therobotoverlord_api.websocket.events import WebSocketEventBroadcaster
from therobotoverlord_api.websocket.events import get_event_broadcaster
from therobotoverlord_api.websocket.manager import WebSocketManager
from therobotoverlord_api.websocket.models import WebSocketEventType


class TestWebSocketEventBroadcaster:
    """Test WebSocket event broadcasting functionality."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        manager = AsyncMock(spec=WebSocketManager)
        manager.send_to_user = AsyncMock()
        manager.broadcast_to_channel = AsyncMock()
        manager.broadcast_to_all = AsyncMock()
        return manager

    @pytest.fixture
    def event_broadcaster(self, mock_websocket_manager):
        """Create event broadcaster instance."""
        return WebSocketEventBroadcaster(mock_websocket_manager)

    @pytest.mark.asyncio
    async def test_broadcast_user_activity_online(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting user online status."""
        user_id = uuid4()
        username = "testuser"

        await event_broadcaster.broadcast_user_activity_update(
            user_id=user_id, username=username, status="online"
        )

        # Verify broadcast to user activity channel
        mock_websocket_manager.broadcast_to_channel.assert_called_once()
        call_args = mock_websocket_manager.broadcast_to_channel.call_args

        channel = call_args[0][0]
        message = call_args[0][1]

        assert channel == "user_activity"
        assert message.event_type == WebSocketEventType.USER_ONLINE
        assert message.data["user_id"] == user_id
        assert message.data["username"] == username

    @pytest.mark.asyncio
    async def test_broadcast_user_activity_offline(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting user offline status."""
        user_id = uuid4()
        username = "testuser"

        await event_broadcaster.broadcast_user_activity_update(
            user_id=user_id, username=username, status="offline"
        )

        # Verify broadcast to user activity channel
        mock_websocket_manager.broadcast_to_channel.assert_called_once()
        call_args = mock_websocket_manager.broadcast_to_channel.call_args

        channel = call_args[0][0]
        message = call_args[0][1]

        assert channel == "user_activity"
        assert message.event_type == WebSocketEventType.USER_OFFLINE
        assert message.data["user_id"] == user_id
        assert message.data["username"] == username

    @pytest.mark.asyncio
    async def test_broadcast_queue_position_update(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting queue position updates."""
        user_id = uuid4()
        queue_type = "posts"
        old_position = 5
        new_position = 3
        total_size = 10

        await event_broadcaster.broadcast_queue_position_update(
            user_id=user_id,
            queue_type=queue_type,
            old_position=old_position,
            new_position=new_position,
            total_queue_size=total_size,
        )

        # Verify message sent to user
        mock_websocket_manager.send_to_user.assert_called_once()
        user_call_args = mock_websocket_manager.send_to_user.call_args

        assert user_call_args[0][0] == user_id
        user_message = user_call_args[0][1]
        assert user_message.event_type == WebSocketEventType.QUEUE_POSITION_UPDATE
        assert user_message.data["old_position"] == old_position
        assert user_message.data["new_position"] == new_position

        # Verify broadcast to queue channel
        mock_websocket_manager.broadcast_to_channel.assert_called_once()
        channel_call_args = mock_websocket_manager.broadcast_to_channel.call_args

        channel = channel_call_args[0][0]
        channel_message = channel_call_args[0][1]

        assert channel == f"queue_{queue_type}"
        assert channel_message.event_type == WebSocketEventType.QUEUE_STATUS_CHANGE
        assert channel_message.data["queue_type"] == queue_type
        assert channel_message.data["total_size"] == total_size

    @pytest.mark.asyncio
    async def test_broadcast_queue_position_update_exception_handling(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test exception handling in queue position update."""
        mock_websocket_manager.send_to_user.side_effect = Exception("WebSocket error")

        user_id = uuid4()

        # Should not raise exception
        await event_broadcaster.broadcast_queue_position_update(
            user_id=user_id,
            queue_type="posts",
            old_position=5,
            new_position=3,
            total_queue_size=10,
        )

    @pytest.mark.asyncio
    async def test_broadcast_content_moderation_result(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting content moderation results."""
        user_id = uuid4()
        content_id = uuid4()
        content_type = "post"
        status = "approved"
        moderator_notes = "Looks good"

        await event_broadcaster.broadcast_content_moderation_result(
            user_id=user_id,
            content_id=content_id,
            content_type=content_type,
            decision=status,
            feedback=moderator_notes,
        )

        # Verify message sent to user
        mock_websocket_manager.send_to_user.assert_called_once()
        call_args = mock_websocket_manager.send_to_user.call_args

        assert call_args[0][0] == user_id
        message = call_args[0][1]
        assert message.event_type == WebSocketEventType.CONTENT_APPROVED
        assert message.data["content_id"] == content_id
        assert message.data["content_type"] == content_type
        assert message.data["decision"] == status
        assert message.data["feedback"] == moderator_notes

    @pytest.mark.asyncio
    async def test_broadcast_content_moderation_result_exception_handling(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test exception handling in content moderation broadcast."""
        mock_websocket_manager.send_to_user.side_effect = Exception("WebSocket error")

        user_id = uuid4()
        content_id = uuid4()

        # Should not raise exception
        await event_broadcaster.broadcast_content_moderation_result(
            user_id=user_id,
            content_id=content_id,
            content_type="post",
            decision="approved",
        )

    @pytest.mark.asyncio
    async def test_broadcast_system_announcement(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting system announcements."""
        title = "System Maintenance"
        message = "Scheduled maintenance tonight"
        announcement_type = "maintenance"
        priority = "high"

        await event_broadcaster.broadcast_system_announcement(
            title=title,
            message=message,
            announcement_type=announcement_type,
            priority=priority,
        )

        # Verify broadcast to announcements channel
        mock_websocket_manager.broadcast_to_channel.assert_called_once()
        call_args = mock_websocket_manager.broadcast_to_channel.call_args

        channel = call_args[0][0]
        ws_message = call_args[0][1]

        assert channel == "announcements"
        assert ws_message.event_type == WebSocketEventType.ANNOUNCEMENT
        assert ws_message.data["title"] == title
        assert ws_message.data["message"] == message
        assert ws_message.data["announcement_type"] == announcement_type
        assert ws_message.data["priority"] == priority

    @pytest.mark.asyncio
    async def test_broadcast_system_announcement_exception_handling(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test exception handling in system announcement broadcast."""
        mock_websocket_manager.broadcast_to_channel.side_effect = Exception(
            "WebSocket error"
        )

        # Should not raise exception
        await event_broadcaster.broadcast_system_announcement(
            title="Test", message="Test message", announcement_type="info"
        )

    @pytest.mark.asyncio
    async def test_broadcast_overlord_chat_message(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting Overlord chat messages."""
        user_id = uuid4()
        message_text = "Hello, citizen!"
        conversation_id = uuid4()
        response_to = uuid4()
        metadata = {"type": "greeting"}

        await event_broadcaster.broadcast_overlord_chat_message(
            user_id=user_id,
            message_text=message_text,
            conversation_id=conversation_id,
            response_to=response_to,
            metadata=metadata,
        )

        # Verify message sent to user
        mock_websocket_manager.send_to_user.assert_called_once()
        call_args = mock_websocket_manager.send_to_user.call_args

        assert call_args[0][0] == user_id
        message = call_args[0][1]
        assert message.event_type == WebSocketEventType.OVERLORD_MESSAGE
        assert message.data["message"] == message_text
        assert message.data["conversation_id"] == conversation_id
        assert message.data["response_to"] == response_to
        assert message.data["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_broadcast_overlord_chat_message_optional_params(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting Overlord chat messages with optional parameters."""
        user_id = uuid4()
        message_text = "Hello!"

        await event_broadcaster.broadcast_overlord_chat_message(
            user_id=user_id, message_text=message_text
        )

        # Verify message sent to user
        mock_websocket_manager.send_to_user.assert_called_once()
        call_args = mock_websocket_manager.send_to_user.call_args

        assert call_args[0][0] == user_id
        message = call_args[0][1]
        assert message.event_type == WebSocketEventType.OVERLORD_MESSAGE
        assert message.data["message"] == message_text
        assert call_args[0][1].data["response_to"] is None
        assert call_args[0][1].data["conversation_id"] is None
        assert call_args[0][1].data["metadata"] == {}

    @pytest.mark.asyncio
    async def test_broadcast_badge_earned(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting badge earned notifications."""
        user_id = uuid4()
        badge_id = uuid4()
        badge_name = "First Post"
        badge_description = "Created your first post"
        badge_icon = "🏆"

        await event_broadcaster.broadcast_badge_earned(
            user_id=user_id,
            badge_id=badge_id,
            badge_name=badge_name,
            badge_description=badge_description,
            badge_icon=badge_icon,
        )

        # Verify message sent to user
        mock_websocket_manager.send_to_user.assert_called_once()
        call_args = mock_websocket_manager.send_to_user.call_args

        assert call_args[0][0] == user_id
        message = call_args[0][1]
        assert message.event_type == WebSocketEventType.BADGE_EARNED
        assert message.data["badge_id"] == str(badge_id)
        assert message.data["badge_name"] == badge_name
        assert message.data["badge_description"] == badge_description
        assert message.data["badge_icon"] == badge_icon

    @pytest.mark.asyncio
    async def test_broadcast_maintenance_mode(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting maintenance mode status."""
        enabled = True
        message = "System maintenance in progress"
        estimated_duration = 30

        await event_broadcaster.broadcast_maintenance_mode(
            enabled=enabled, message=message, estimated_duration=estimated_duration
        )

        # Verify broadcast to all users
        mock_websocket_manager.broadcast_to_all.assert_called_once()
        call_args = mock_websocket_manager.broadcast_to_all.call_args

        ws_message = call_args[0][0]
        assert ws_message.event_type == WebSocketEventType.MAINTENANCE_MODE
        assert ws_message.data["enabled"] == enabled
        assert ws_message.data["message"] == message
        assert ws_message.data["estimated_duration"] == estimated_duration

    @pytest.mark.asyncio
    async def test_broadcast_maintenance_mode_minimal_params(
        self, event_broadcaster, mock_websocket_manager
    ):
        """Test broadcasting maintenance mode with minimal parameters."""
        await event_broadcaster.broadcast_maintenance_mode(enabled=False)

        # Verify broadcast to all users
        mock_websocket_manager.broadcast_to_all.assert_called_once()
        call_args = mock_websocket_manager.broadcast_to_all.call_args

        ws_message = call_args[0][0]
        assert ws_message.data["enabled"] is False
        assert ws_message.data["message"] is None
        assert ws_message.data["estimated_duration"] is None


class TestEventBroadcasterFactory:
    """Test event broadcaster factory function."""

    def test_get_event_broadcaster_creates_instance(self):
        """Test that get_event_broadcaster creates new instance."""
        mock_manager = MagicMock(spec=WebSocketManager)

        broadcaster = get_event_broadcaster(mock_manager)

        assert isinstance(broadcaster, WebSocketEventBroadcaster)
        assert broadcaster.websocket_manager == mock_manager

    def test_get_event_broadcaster_caches_instance(self):
        """Test that get_event_broadcaster caches instances per manager."""
        mock_manager1 = MagicMock(spec=WebSocketManager)
        mock_manager2 = MagicMock(spec=WebSocketManager)

        broadcaster1a = get_event_broadcaster(mock_manager1)
        broadcaster1b = get_event_broadcaster(mock_manager1)
        broadcaster2 = get_event_broadcaster(mock_manager2)

        # Same manager should return same instance
        assert broadcaster1a is broadcaster1b

        # Different manager should return different instance
        assert broadcaster1a is not broadcaster2

    def test_get_event_broadcaster_cache_isolation(self):
        """Test that cache properly isolates different manager instances."""
        # Clear any existing cache
        from therobotoverlord_api.websocket.events import _event_broadcaster_cache

        _event_broadcaster_cache.clear()

        mock_manager1 = MagicMock(spec=WebSocketManager)
        mock_manager2 = MagicMock(spec=WebSocketManager)

        broadcaster1 = get_event_broadcaster(mock_manager1)
        broadcaster2 = get_event_broadcaster(mock_manager2)

        assert len(_event_broadcaster_cache) == 2
        assert broadcaster1 is not broadcaster2
