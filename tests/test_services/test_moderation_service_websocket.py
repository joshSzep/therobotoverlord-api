"""Tests for moderation service WebSocket integration."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.services.moderation_service import ModerationService
from therobotoverlord_api.websocket.manager import WebSocketManager


class TestModerationServiceWebSocket:
    """Test moderation service WebSocket integration."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        return AsyncMock(spec=WebSocketManager)

    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        db = AsyncMock()
        db.fetchrow = AsyncMock()
        db.fetch = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def moderation_service(self, mock_db):
        """Create moderation service instance."""
        service = ModerationService()
        service.db = mock_db
        return service

    @pytest.mark.asyncio
    async def test_approve_content_with_websocket_broadcast(
        self, moderation_service, mock_db, mock_websocket_manager
    ):
        """Test content approval with WebSocket broadcast."""
        content_id = uuid4()
        user_id = uuid4()
        moderator_id = uuid4()
        content_type = "post"
        moderator_notes = "Content looks good"

        # Mock database responses
        mock_db.fetchrow.return_value = {"user_pk": user_id, "status": "pending"}
        mock_db.execute.return_value = None
        mock_db.fetch.return_value = []  # No remaining items in queue

        with patch(
            "therobotoverlord_api.services.moderation_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            await moderation_service.approve_content(
                content_id=content_id,
                content_type=content_type,
                moderator_id=moderator_id,
                moderator_notes=moderator_notes,
                websocket_manager=mock_websocket_manager,
            )

            # Verify moderation result was broadcasted
            mock_broadcaster.broadcast_content_moderation_result.assert_called_once_with(
                user_id=user_id,
                content_id=content_id,
                content_type=content_type,
                decision="approved",
                feedback=moderator_notes,
            )

    @pytest.mark.asyncio
    async def test_reject_content_with_websocket_broadcast(
        self, moderation_service, mock_db, mock_websocket_manager
    ):
        """Test content rejection with WebSocket broadcast."""
        content_id = uuid4()
        user_id = uuid4()
        moderator_id = uuid4()
        content_type = "topic"
        moderator_notes = "Violates community guidelines"

        # Mock database responses
        mock_db.fetchrow.return_value = {"user_pk": user_id, "status": "pending"}
        mock_db.execute.return_value = None
        mock_db.fetch.return_value = []

        with patch(
            "therobotoverlord_api.services.moderation_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            await moderation_service.reject_content(
                content_id=content_id,
                content_type=content_type,
                moderator_id=moderator_id,
                moderator_notes=moderator_notes,
                websocket_manager=mock_websocket_manager,
            )

            # Verify moderation result was broadcasted
            mock_broadcaster.broadcast_content_moderation_result.assert_called_once_with(
                user_id=user_id,
                content_id=content_id,
                content_type=content_type,
                decision="rejected",
                feedback=moderator_notes,
            )

    @pytest.mark.asyncio
    async def test_approve_content_with_queue_position_updates(
        self, moderation_service, mock_db, mock_websocket_manager
    ):
        """Test content approval broadcasts queue position updates."""
        content_id = uuid4()
        user_id = uuid4()
        moderator_id = uuid4()
        content_type = "post"

        # Mock database responses
        mock_db.fetchrow.side_effect = [
            {"user_pk": user_id, "status": "pending"},  # Content lookup
            {"total": 5},  # Total queue size
        ]
        mock_db.execute.return_value = None

        # Mock remaining user items in queue
        mock_db.fetch.return_value = [
            {"pk": uuid4(), "user_pk": user_id},
            {"pk": uuid4(), "user_pk": user_id},
        ]

        with patch(
            "therobotoverlord_api.services.moderation_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            await moderation_service.approve_content(
                content_id=content_id,
                content_type=content_type,
                moderator_id=moderator_id,
                websocket_manager=mock_websocket_manager,
            )

            # Verify queue position updates were broadcasted
            assert mock_broadcaster.broadcast_queue_position_update.call_count == 2

            # Check first position update
            first_call = (
                mock_broadcaster.broadcast_queue_position_update.call_args_list[0]
            )
            assert first_call[1]["user_id"] == user_id
            assert first_call[1]["queue_type"] == f"{content_type}_moderation"
            assert first_call[1]["new_position"] == 1
            assert first_call[1]["total_queue_size"] == 5

    @pytest.mark.asyncio
    async def test_moderation_without_websocket_manager(
        self, moderation_service, mock_db
    ):
        """Test moderation works without WebSocket manager."""
        content_id = uuid4()
        user_id = uuid4()
        moderator_id = uuid4()
        content_type = "post"

        # Mock database responses
        mock_db.fetchrow.return_value = {"user_pk": user_id, "status": "pending"}
        mock_db.execute.return_value = None

        # Should not raise exception when websocket_manager is None
        await moderation_service.approve_content(
            content_id=content_id,
            content_type=content_type,
            moderator_id=moderator_id,
            websocket_manager=None,
        )

    @pytest.mark.asyncio
    async def test_moderation_content_not_found(
        self, moderation_service, mock_db, mock_websocket_manager
    ):
        """Test moderation when content is not found."""
        content_id = uuid4()
        moderator_id = uuid4()
        content_type = "post"

        # Mock content not found
        mock_db.fetchrow.return_value = None

        with patch(
            "therobotoverlord_api.services.moderation_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            await moderation_service.approve_content(
                content_id=content_id,
                content_type=content_type,
                moderator_id=moderator_id,
                websocket_manager=mock_websocket_manager,
            )

            # Should not broadcast when content not found
            mock_broadcaster.broadcast_content_moderation_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_moderation_already_processed(
        self, moderation_service, mock_db, mock_websocket_manager
    ):
        """Test moderation when content is already processed."""
        content_id = uuid4()
        user_id = uuid4()
        moderator_id = uuid4()
        content_type = "post"

        # Mock already processed content
        mock_db.fetchrow.return_value = {"user_pk": user_id, "status": "approved"}

        with patch(
            "therobotoverlord_api.services.moderation_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            await moderation_service.approve_content(
                content_id=content_id,
                content_type=content_type,
                moderator_id=moderator_id,
                websocket_manager=mock_websocket_manager,
            )

            # Should not broadcast when already processed
            mock_broadcaster.broadcast_content_moderation_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_moderation_websocket_error_handling(
        self, moderation_service, mock_db, mock_websocket_manager
    ):
        """Test moderation handles WebSocket errors gracefully."""
        content_id = uuid4()
        user_id = uuid4()
        moderator_id = uuid4()
        content_type = "post"

        # Mock database responses
        mock_db.fetchrow.return_value = {"user_pk": user_id, "status": "pending"}
        mock_db.execute.return_value = None
        mock_db.fetch.return_value = []

        with patch(
            "therobotoverlord_api.services.moderation_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_broadcaster.broadcast_content_moderation_result.side_effect = (
                Exception("WebSocket error")
            )
            mock_get_broadcaster.return_value = mock_broadcaster

            # Should not raise exception even if WebSocket fails
            await moderation_service.approve_content(
                content_id=content_id,
                content_type=content_type,
                moderator_id=moderator_id,
                websocket_manager=mock_websocket_manager,
            )

    @pytest.mark.asyncio
    async def test_bulk_moderation_with_websocket(
        self, moderation_service, mock_db, mock_websocket_manager
    ):
        """Test bulk moderation operations with WebSocket broadcasts."""
        content_ids = [uuid4(), uuid4(), uuid4()]
        user_ids = [uuid4(), uuid4(), uuid4()]
        moderator_id = uuid4()
        content_type = "post"

        # Mock database responses for each content item
        mock_db.fetchrow.side_effect = [
            {"user_pk": user_ids[0], "status": "pending"},
            {"user_pk": user_ids[1], "status": "pending"},
            {"user_pk": user_ids[2], "status": "pending"},
        ]
        mock_db.execute.return_value = None
        mock_db.fetch.return_value = []

        with patch(
            "therobotoverlord_api.services.moderation_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            # Process each content item
            for _i, content_id in enumerate(content_ids):
                await moderation_service.approve_content(
                    content_id=content_id,
                    content_type=content_type,
                    moderator_id=moderator_id,
                    websocket_manager=mock_websocket_manager,
                )

            # Verify all broadcasts were made
            assert mock_broadcaster.broadcast_content_moderation_result.call_count == 3

            # Verify each user got their notification
            for i, user_id in enumerate(user_ids):
                call_args = (
                    mock_broadcaster.broadcast_content_moderation_result.call_args_list[
                        i
                    ]
                )
                assert call_args[1]["user_id"] == user_id
                assert call_args[1]["content_id"] == content_ids[i]

    @pytest.mark.asyncio
    async def test_different_content_types_websocket_broadcast(
        self, moderation_service, mock_db, mock_websocket_manager
    ):
        """Test WebSocket broadcasts work for different content types."""
        content_types = ["post", "topic", "private_message"]

        for content_type in content_types:
            content_id = uuid4()
            user_id = uuid4()
            moderator_id = uuid4()

            # Mock database responses
            mock_db.fetchrow.return_value = {"user_pk": user_id, "status": "pending"}
            mock_db.execute.return_value = None
            mock_db.fetch.return_value = []

            with patch(
                "therobotoverlord_api.services.moderation_service.get_event_broadcaster"
            ) as mock_get_broadcaster:
                mock_broadcaster = AsyncMock()
                mock_get_broadcaster.return_value = mock_broadcaster

                await moderation_service.approve_content(
                    content_id=content_id,
                    content_type=content_type,
                    moderator_id=moderator_id,
                    websocket_manager=mock_websocket_manager,
                )

                # Verify broadcast includes correct content type
                mock_broadcaster.broadcast_content_moderation_result.assert_called_once_with(
                    user_id=user_id,
                    content_id=content_id,
                    content_type=content_type,
                    decision="approved",
                    feedback=None,
                )

                mock_broadcaster.reset_mock()
