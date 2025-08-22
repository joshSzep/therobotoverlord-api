"""Tests for WebSocket connection manager."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import WebSocket

from therobotoverlord_api.websocket.manager import WebSocketManager
from therobotoverlord_api.websocket.models import WebSocketConnectionInfo
from therobotoverlord_api.websocket.models import WebSocketEventType
from therobotoverlord_api.websocket.models import WebSocketMessage


class TestWebSocketManager:
    """Test WebSocket connection manager."""

    @pytest.fixture
    def manager(self):
        """Create WebSocket manager instance."""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock(return_value=None)
        websocket.close = AsyncMock(return_value=None)
        websocket.send_text = AsyncMock(return_value=None)
        websocket.send_json = AsyncMock(return_value=None)
        return websocket

    @pytest.mark.asyncio
    async def test_connect_new_connection(self, manager, mock_websocket):
        """Test connecting a new WebSocket."""
        user_id = uuid4()

        connection_id = await manager.connect(mock_websocket, user_id)

        # Verify connection was accepted
        mock_websocket.accept.assert_called_once()

        # Verify connection is stored
        assert connection_id in manager.active_connections
        assert manager.active_connections[connection_id] == mock_websocket

        # Verify user connection tracking
        assert user_id in manager.user_connections
        assert connection_id in manager.user_connections[user_id]

        # Verify connection info is stored
        assert connection_id in manager.connection_info
        connection_info = manager.connection_info[connection_id]
        assert connection_info.user_id == user_id
        assert connection_info.connection_id == connection_id

    @pytest.mark.asyncio
    async def test_connect_multiple_connections_same_user(
        self, manager, mock_websocket
    ):
        """Test multiple connections for the same user."""
        user_id = uuid4()
        websocket2 = AsyncMock(spec=WebSocket)

        connection_id1 = await manager.connect(mock_websocket, user_id)
        connection_id2 = await manager.connect(websocket2, user_id)

        # Verify both connections are tracked
        assert len(manager.user_connections[user_id]) == 2
        assert connection_id1 in manager.user_connections[user_id]
        assert connection_id2 in manager.user_connections[user_id]

    @pytest.mark.asyncio
    async def test_disconnect_existing_connection(self, manager, mock_websocket):
        """Test disconnecting an existing connection."""
        user_id = uuid4()
        connection_id = await manager.connect(mock_websocket, user_id)

        # Subscribe to a channel first
        manager.subscribe_to_channel(connection_id, "test_channel")

        await manager.disconnect(connection_id)

        # Verify connection is removed
        assert connection_id not in manager.active_connections
        assert connection_id not in manager.connection_info

        # Verify user connections are cleaned up
        assert user_id not in manager.user_connections

        # Verify subscriptions are cleaned up
        assert "test_channel" not in manager.subscriptions

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self, manager):
        """Test disconnecting a non-existent connection."""
        # Should not raise an exception
        await manager.disconnect("nonexistent_id")

    @pytest.mark.asyncio
    async def test_disconnect_partial_user_connections(self, manager, mock_websocket):
        """Test disconnecting one of multiple user connections."""
        user_id = uuid4()
        websocket2 = AsyncMock(spec=WebSocket)

        connection_id1 = await manager.connect(mock_websocket, user_id)
        connection_id2 = await manager.connect(websocket2, user_id)

        await manager.disconnect(connection_id1)

        # Verify only one connection is removed
        assert connection_id1 not in manager.active_connections
        assert connection_id2 in manager.active_connections

        # Verify user still has remaining connection
        assert user_id in manager.user_connections
        assert connection_id2 in manager.user_connections[user_id]
        assert connection_id1 not in manager.user_connections[user_id]

    def test_subscribe_to_channel(self, manager, mock_websocket):
        """Test subscribing to a channel."""
        user_id = uuid4()

        with patch.object(
            manager, "connect", return_value="test_connection_id"
        ) as mock_connect:
            connection_id = "test_connection_id"
            manager.active_connections[connection_id] = mock_websocket
            manager.connection_info[connection_id] = WebSocketConnectionInfo(
                connection_id=connection_id,
                user_id=user_id,
                connected_at=datetime.now(UTC),
                last_ping=datetime.now(UTC),
                subscriptions=[],
            )

            manager.subscribe_to_channel(connection_id, "test_channel")

            # Verify subscription is added
            assert "test_channel" in manager.subscriptions
            assert connection_id in manager.subscriptions["test_channel"]

            # Verify connection info is updated
            assert (
                "test_channel" in manager.connection_info[connection_id].subscriptions
            )

    def test_subscribe_to_channel_nonexistent_connection(self, manager):
        """Test subscribing non-existent connection to channel."""
        # Should not raise an exception
        manager.subscribe_to_channel("nonexistent_id", "test_channel")

    def test_unsubscribe_from_channel(self, manager, mock_websocket):
        """Test unsubscribing from a channel."""
        user_id = uuid4()
        connection_id = "test_connection_id"

        manager.active_connections[connection_id] = mock_websocket
        manager.connection_info[connection_id] = WebSocketConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            connected_at=datetime.now(UTC),
            last_ping=datetime.now(UTC),
            subscriptions=["test_channel"],
        )
        manager.subscriptions["test_channel"] = [connection_id]

        manager.unsubscribe_from_channel(connection_id, "test_channel")

        # Verify subscription is removed
        assert "test_channel" not in manager.subscriptions

        # Verify connection info is updated
        assert (
            "test_channel" not in manager.connection_info[connection_id].subscriptions
        )

    def test_get_user_connections(self, manager, mock_websocket):
        """Test getting user connections."""
        user_id = uuid4()
        connection_id = "test_connection_id"

        manager.user_connections[user_id] = [connection_id]

        connections = manager.get_user_connections(user_id)
        assert connections == [connection_id]

        # Test non-existent user
        empty_connections = manager.get_user_connections(uuid4())
        assert empty_connections == []

    def test_get_channel_subscribers(self, manager):
        """Test getting channel subscribers."""
        connection_id = "test_connection_id"
        manager.subscriptions["test_channel"] = [connection_id]

        subscribers = manager.get_channel_subscribers("test_channel")
        assert subscribers == [connection_id]

        # Test non-existent channel
        empty_subscribers = manager.get_channel_subscribers("nonexistent_channel")
        assert empty_subscribers == []

    def test_is_user_online(self, manager, mock_websocket):
        """Test checking if user is online."""
        user_id = uuid4()

        # User not online initially
        assert manager.is_user_online(user_id) is False

        # Add user connection
        manager.user_connections[user_id] = ["test_connection_id"]
        assert manager.is_user_online(user_id) is True

        # Remove user connections
        manager.user_connections[user_id] = []
        assert manager.is_user_online(user_id) is False

    @pytest.mark.asyncio
    async def test_send_to_connection(self, manager, mock_websocket):
        """Test sending message to specific connection."""
        connection_id = "test_connection_id"
        manager.active_connections[connection_id] = mock_websocket

        message = WebSocketMessage(
            event_type=WebSocketEventType.CONNECT, data={"test": "data"}
        )

        await manager.send_to_connection(connection_id, message)

        mock_websocket.send_text.assert_called_once()
        sent_data = mock_websocket.send_text.call_args[0][0]
        assert "test" in sent_data
        assert "connect" in sent_data

    @pytest.mark.asyncio
    async def test_send_to_connection_nonexistent(self, manager):
        """Test sending message to non-existent connection."""
        message = WebSocketMessage(
            event_type=WebSocketEventType.CONNECT, data={"test": "data"}
        )

        # Should not raise an exception
        await manager.send_to_connection("nonexistent_id", message)

    @pytest.mark.asyncio
    async def test_send_to_connection_websocket_error(self, manager, mock_websocket):
        """Test handling WebSocket error when sending."""
        connection_id = "test_connection_id"
        manager.active_connections[connection_id] = mock_websocket
        manager.connection_info[connection_id] = WebSocketConnectionInfo(
            connection_id=connection_id,
            user_id=uuid4(),
            connected_at=datetime.now(UTC),
            last_ping=datetime.now(UTC),
            subscriptions=[],
        )

        # Mock WebSocket error
        mock_websocket.send_text.side_effect = Exception("Connection closed")

        message = WebSocketMessage(
            event_type=WebSocketEventType.CONNECT, data={"test": "data"}
        )

        with patch.object(manager, "disconnect") as mock_disconnect:
            await manager.send_to_connection(connection_id, message)
            mock_disconnect.assert_called_once_with(connection_id)

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager, mock_websocket):
        """Test sending message to user."""
        user_id = uuid4()
        connection_id = "test_connection_id"

        manager.active_connections[connection_id] = mock_websocket
        manager.user_connections[user_id] = [connection_id]

        message = WebSocketMessage(
            event_type=WebSocketEventType.USER_ONLINE, data={"user_id": str(user_id)}
        )

        await manager.send_to_user(user_id, message)

        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_user_multiple_connections(self, manager, mock_websocket):
        """Test sending message to user with multiple connections."""
        user_id = uuid4()
        websocket2 = AsyncMock()
        websocket2.send_text = AsyncMock()
        websocket2.send_json = AsyncMock()
        websocket2.close = AsyncMock()

        connection_id1 = "test_connection_id1"
        connection_id2 = "test_connection_id2"

        manager.active_connections[connection_id1] = mock_websocket
        manager.active_connections[connection_id2] = websocket2
        manager.user_connections[user_id] = [connection_id1, connection_id2]

        message = WebSocketMessage(
            event_type=WebSocketEventType.USER_ONLINE, data={"user_id": str(user_id)}
        )

        await manager.send_to_user(user_id, message)

        # Both connections should receive the message
        mock_websocket.send_text.assert_called_once()
        websocket2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, manager, mock_websocket):
        """Test broadcasting message to channel."""
        connection_id = "test_connection_id"
        manager.active_connections[connection_id] = mock_websocket
        manager.subscriptions["test_channel"] = [connection_id]

        message = WebSocketMessage(
            event_type=WebSocketEventType.ANNOUNCEMENT,
            data={"message": "Test announcement"},
        )

        await manager.broadcast_to_channel("test_channel", message)

        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, manager, mock_websocket):
        """Test broadcasting message to all connections."""
        websocket2 = AsyncMock()
        websocket2.send_text = AsyncMock()
        websocket2.send_json = AsyncMock()
        websocket2.close = AsyncMock()

        manager.active_connections["conn1"] = mock_websocket
        manager.active_connections["conn2"] = websocket2

        message = WebSocketMessage(
            event_type=WebSocketEventType.MAINTENANCE_MODE, data={"enabled": True}
        )

        await manager.broadcast_to_all(message)

        # Both connections should receive the message
        mock_websocket.send_text.assert_called_once()
        websocket2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_ping(self, manager, mock_websocket):
        """Test handling ping from client."""
        connection_id = "test_connection_id"
        user_id = uuid4()

        manager.active_connections[connection_id] = mock_websocket
        manager.connection_info[connection_id] = WebSocketConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            connected_at=datetime.now(UTC),
            last_ping=datetime.now(UTC),
            subscriptions=[],
        )

        await manager.handle_ping(connection_id)

        # Should send pong response
        mock_websocket.send_text.assert_called_once()
        sent_data = mock_websocket.send_text.call_args[0][0]
        import json

        message_data = json.loads(sent_data)
        assert message_data["data"]["type"] == "pong"

    @pytest.mark.asyncio
    async def test_handle_ping_nonexistent_connection(self, manager):
        """Test handling ping for non-existent connection."""
        # Should not raise an exception
        await manager.handle_ping("nonexistent_id")
