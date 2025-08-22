"""Tests for queue service WebSocket integration."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.services.queue_service import QueueService
from therobotoverlord_api.websocket.manager import WebSocketManager


class TestQueueServiceWebSocket:
    """Test queue service WebSocket integration."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        return AsyncMock(spec=WebSocketManager)

    @pytest.fixture
    def mock_queue_repo(self):
        """Create mock queue repository."""
        repo = AsyncMock()
        repo.add_to_queue = AsyncMock()
        repo.get_user_position = AsyncMock()
        repo.get_queue_size = AsyncMock()
        repo.remove_from_queue = AsyncMock()
        repo.get_next_items = AsyncMock()
        return repo

    @pytest.fixture
    def queue_service(self, mock_queue_repo):
        """Create queue service instance."""
        service = QueueService()
        service.queue_repo = mock_queue_repo
        return service

    @pytest.mark.asyncio
    async def test_add_to_queue_with_websocket_broadcast(
        self, queue_service, mock_queue_repo, mock_websocket_manager
    ):
        """Test adding item to queue with WebSocket broadcast."""
        user_id = uuid4()
        content_id = uuid4()
        queue_type = "posts"
        priority = 1

        # Mock repository responses
        mock_queue_repo.add_to_queue.return_value = {"pk": uuid4()}
        mock_queue_repo.get_user_position.return_value = 1
        mock_queue_repo.get_queue_size.return_value = 5

        with (
            patch(
                "therobotoverlord_api.services.queue_service.get_event_broadcaster"
            ) as mock_get_broadcaster,
            patch.object(queue_service, "add_post_to_queue") as mock_add_post,
        ):
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster
            mock_add_post.return_value = {"pk": uuid4()}

            await queue_service.add_to_queue(
                user_id=user_id,
                content_id=content_id,
                queue_type=queue_type,
                priority=priority,
                websocket_manager=mock_websocket_manager,
            )

            # Verify queue position update was broadcasted
            mock_broadcaster.broadcast_queue_position_update.assert_called_once_with(
                user_id=user_id,
                queue_type=queue_type,
                old_position=None,
                new_position=1,
                total_queue_size=5,
            )

    @pytest.mark.asyncio
    async def test_remove_from_queue_with_websocket_broadcast(
        self, queue_service, mock_queue_repo, mock_websocket_manager
    ):
        """Test removing item from queue with WebSocket broadcast."""
        user_id = uuid4()
        content_id = uuid4()
        queue_type = "topics"

        # Mock repository responses
        mock_queue_repo.get_user_position.side_effect = [
            5,
            None,
        ]  # Before and after removal
        mock_queue_repo.get_queue_size.return_value = 8
        mock_queue_repo.remove_from_queue.return_value = True

        with (
            patch(
                "therobotoverlord_api.services.queue_service.get_event_broadcaster"
            ) as mock_get_broadcaster,
            patch.object(queue_service, "remove_topic_from_queue") as mock_remove_topic,
        ):
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster
            mock_remove_topic.return_value = True

            result = await queue_service.remove_from_queue(
                user_id=user_id,
                content_id=content_id,
                queue_type=queue_type,
                websocket_manager=mock_websocket_manager,
            )

            assert result is True

            # Verify queue position update was broadcasted
            mock_broadcaster.broadcast_queue_position_update.assert_called_once_with(
                user_id=user_id,
                queue_type=queue_type,
                old_position=3,
                new_position=0,
                total_queue_size=10,
            )

    @pytest.mark.asyncio
    async def test_process_queue_items_with_websocket_broadcast(
        self, queue_service, mock_queue_repo, mock_websocket_manager
    ):
        """Test processing queue items with WebSocket broadcasts."""
        queue_type = "posts"
        batch_size = 2

        # Mock queue items
        queue_items = [
            {"pk": uuid4(), "user_pk": uuid4(), "content_id": uuid4()},
            {"pk": uuid4(), "user_pk": uuid4(), "content_id": uuid4()},
        ]

        mock_queue_repo.get_next_items.return_value = queue_items
        mock_queue_repo.get_user_position.return_value = 1
        mock_queue_repo.get_queue_size.return_value = 5

        with (
            patch(
                "therobotoverlord_api.services.queue_service.get_event_broadcaster"
            ) as mock_get_broadcaster,
            patch.object(queue_service, "get_post_queue_items") as mock_get_items,
        ):
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster
            mock_get_items.return_value = queue_items

            processed_items = await queue_service.process_queue_items(
                queue_type=queue_type,
                batch_size=batch_size,
                websocket_manager=mock_websocket_manager,
            )

            assert len(processed_items) == 2

            # Verify position updates were broadcasted for each user
            assert mock_broadcaster.broadcast_queue_position_update.call_count == 2

            for i, item in enumerate(queue_items):
                call_args = (
                    mock_broadcaster.broadcast_queue_position_update.call_args_list[i]
                )
                assert call_args[1]["user_id"] == item["user_pk"]
                assert call_args[1]["queue_type"] == queue_type

    @pytest.mark.asyncio
    async def test_update_queue_priority_with_websocket_broadcast(
        self, queue_service, mock_queue_repo, mock_websocket_manager
    ):
        """Test updating queue priority with WebSocket broadcast."""
        user_id = uuid4()
        content_id = uuid4()
        queue_type = "posts"
        new_priority = 5

        # Mock repository responses
        mock_queue_repo.get_user_position.side_effect = [
            3,
            2,
        ]  # Position changes due to priority
        mock_queue_repo.get_queue_size.return_value = 10
        mock_queue_repo.update_priority = AsyncMock(return_value=True)

        with patch(
            "therobotoverlord_api.services.queue_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            await queue_service.update_queue_priority(
                user_id=user_id,
                content_id=content_id,
                queue_type=queue_type,
                new_priority=new_priority,
                websocket_manager=mock_websocket_manager,
            )

            # Verify position update was broadcasted
            mock_broadcaster.broadcast_queue_position_update.assert_called_once_with(
                user_id=user_id,
                queue_type=queue_type,
                old_position=3,
                new_position=2,
                total_queue_size=10,
            )

    @pytest.mark.asyncio
    async def test_queue_operations_without_websocket_manager(
        self, queue_service, mock_queue_repo
    ):
        """Test queue operations work without WebSocket manager."""
        user_id = uuid4()
        content_id = uuid4()
        queue_type = "posts"

        # Mock repository responses
        mock_queue_repo.add_to_queue.return_value = {"pk": uuid4()}
        mock_queue_repo.get_user_position.return_value = 1
        mock_queue_repo.get_queue_size.return_value = 5

        # Should not raise exception when websocket_manager is None
        await queue_service.add_to_queue(
            user_id=user_id,
            content_id=content_id,
            queue_type=queue_type,
            priority=1,
            websocket_manager=None,
        )

    @pytest.mark.asyncio
    async def test_queue_websocket_error_handling(
        self, queue_service, mock_queue_repo, mock_websocket_manager
    ):
        """Test queue service handles WebSocket errors gracefully."""
        user_id = uuid4()
        content_id = uuid4()
        queue_type = "posts"

        # Mock repository responses
        mock_queue_repo.add_to_queue.return_value = {"pk": uuid4()}
        mock_queue_repo.get_user_position.return_value = 1
        mock_queue_repo.get_queue_size.return_value = 5

        with patch(
            "therobotoverlord_api.services.queue_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_broadcaster.broadcast_queue_position_update.side_effect = Exception(
                "WebSocket error"
            )
            mock_get_broadcaster.return_value = mock_broadcaster

            # Should not raise exception even if WebSocket fails
            await queue_service.add_to_queue(
                user_id=user_id,
                content_id=content_id,
                queue_type=queue_type,
                priority=1,
                websocket_manager=mock_websocket_manager,
            )

    @pytest.mark.asyncio
    async def test_get_queue_status_with_websocket_broadcast(
        self, queue_service, mock_queue_repo, mock_websocket_manager
    ):
        """Test getting queue status with WebSocket broadcast."""
        user_id = uuid4()
        queue_type = "posts"

        # Mock repository responses
        mock_queue_repo.get_user_position.return_value = 4
        mock_queue_repo.get_queue_size.return_value = 12
        mock_queue_repo.get_user_items_in_queue = AsyncMock(
            return_value=[{"pk": uuid4(), "content_id": uuid4(), "priority": 1}]
        )

        with (
            patch(
                "therobotoverlord_api.services.queue_service.get_event_broadcaster"
            ) as mock_get_broadcaster,
            patch.object(queue_service, "get_post_queue_status") as mock_get_status,
        ):
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster
            mock_get_status.return_value = {
                "status": "active",
                "size": 0,
                "avg_priority": 0.0,
                "items": [],
            }

            status = await queue_service.get_queue_status(
                user_id=user_id,
                queue_type=queue_type,
                websocket_manager=mock_websocket_manager,
            )

            assert status["position"] == 4
            assert status["total_size"] == 12
            assert len(status["user_items"]) == 1

    @pytest.mark.asyncio
    async def test_bulk_queue_operations_with_websocket(
        self, queue_service, mock_queue_repo, mock_websocket_manager
    ):
        """Test bulk queue operations with WebSocket broadcasts."""
        user_ids = [uuid4(), uuid4(), uuid4()]
        content_ids = [uuid4(), uuid4(), uuid4()]
        queue_type = "posts"

        # Mock repository responses
        mock_queue_repo.add_to_queue.return_value = {"pk": uuid4()}
        mock_queue_repo.get_user_position.side_effect = [1, 2, 3]
        mock_queue_repo.get_queue_size.side_effect = [1, 2, 3]

        with (
            patch(
                "therobotoverlord_api.services.queue_service.get_event_broadcaster"
            ) as mock_get_broadcaster,
            patch.object(queue_service, "add_post_to_queue") as mock_add_post,
        ):
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster
            mock_add_post.return_value = True

            # Add multiple items to queue
            for _i, (user_id, content_id) in enumerate(
                zip(user_ids, content_ids, strict=False)
            ):
                await queue_service.add_to_queue(
                    user_id=user_id,
                    content_id=content_id,
                    queue_type=queue_type,
                    priority=1,
                    websocket_manager=mock_websocket_manager,
                )

            # Verify all broadcasts were made
            assert mock_broadcaster.broadcast_queue_position_update.call_count == 3

            # Verify each user got their position update
            for i, user_id in enumerate(user_ids):
                call_args = (
                    mock_broadcaster.broadcast_queue_position_update.call_args_list[i]
                )
                assert call_args[1]["user_id"] == user_id
                assert call_args[1]["new_position"] == i + 1

    @pytest.mark.asyncio
    async def test_queue_position_no_change_no_broadcast(
        self, queue_service, mock_queue_repo, mock_websocket_manager
    ):
        """Test no broadcast when queue position doesn't change."""
        user_id = uuid4()
        content_id = uuid4()
        queue_type = "posts"

        # Mock repository responses - position stays the same
        mock_queue_repo.get_user_position.return_value = 3
        mock_queue_repo.get_queue_size.return_value = 10
        mock_queue_repo.update_priority = AsyncMock(return_value=False)  # No change

        with patch(
            "therobotoverlord_api.services.queue_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            await queue_service.update_queue_priority(
                user_id=user_id,
                content_id=content_id,
                queue_type=queue_type,
                new_priority=1,
                websocket_manager=mock_websocket_manager,
            )

            # Should not broadcast if no actual change occurred
            mock_broadcaster.broadcast_queue_position_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_different_queue_types_websocket_broadcast(
        self, queue_service, mock_queue_repo, mock_websocket_manager
    ):
        """Test WebSocket broadcasts work for different queue types."""
        queue_types = ["posts", "topics", "private_messages"]

        for queue_type in queue_types:
            user_id = uuid4()
            content_id = uuid4()

            # Mock repository responses
            mock_queue_repo.add_to_queue.return_value = {"pk": uuid4()}
            mock_queue_repo.get_user_position.return_value = 1
            mock_queue_repo.get_queue_size.return_value = 5

            with (
                patch(
                    "therobotoverlord_api.services.queue_service.get_event_broadcaster"
                ) as mock_get_broadcaster,
                patch.object(
                    queue_service, "add_post_to_queue", new_callable=AsyncMock
                ) as mock_add_post,
                patch.object(
                    queue_service, "add_topic_to_queue", new_callable=AsyncMock
                ) as mock_add_topic,
                patch.object(
                    queue_service, "add_message_to_queue", new_callable=AsyncMock
                ) as mock_add_message,
            ):
                mock_broadcaster = AsyncMock()
                mock_get_broadcaster.return_value = mock_broadcaster

                # Mock the specific add methods to return success
                mock_add_post.return_value = True
                mock_add_topic.return_value = True
                mock_add_message.return_value = True

                await queue_service.add_to_queue(
                    user_id=user_id,
                    content_id=content_id,
                    queue_type=queue_type,
                    priority=1,
                    websocket_manager=mock_websocket_manager,
                )

                # Verify broadcast includes correct queue type
                mock_broadcaster.broadcast_queue_position_update.assert_called_once_with(
                    user_id=user_id,
                    queue_type=queue_type,
                    old_position=None,
                    new_position=1,
                    total_queue_size=5,
                )

                mock_broadcaster.reset_mock()
