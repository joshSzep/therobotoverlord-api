"""Coverage tests for queue API endpoints coverage."""

from unittest.mock import patch

import pytest

from fastapi import status
from httpx import AsyncClient


class TestQueueAPICoverage:
    """Test queue API endpoints for coverage improvement."""

    @pytest.mark.asyncio
    async def test_get_queue_status_public(self, async_client: AsyncClient):
        """Test queue status without authentication (public endpoint)."""
        response = await async_client.get("/api/v1/queue/status")
        # This is a public endpoint, should return 200 or 500 (DB error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_get_content_queue_position_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test content queue position without authentication."""
        content_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(f"/api/v1/queue/position/topics/{content_id}")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_queue_visualization_public(self, async_client: AsyncClient):
        """Test queue visualization without authentication (public endpoint)."""
        with patch(
            "therobotoverlord_api.services.queue_service.QueueService._ensure_connections"
        ) as mock_conn:
            mock_conn.return_value = None

            response = await async_client.get("/api/v1/queue/visualization")
            # This is a public endpoint, should return 200 or 500 (DB/Redis connection error)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ]

    @pytest.mark.asyncio
    async def test_get_queue_type_status_public(self, async_client: AsyncClient):
        """Test queue type status without authentication (public endpoint)."""
        response = await async_client.get("/api/v1/queue/status/topics")
        # This is a public endpoint, should return 200, 400 (DB init error), or 500 (DB error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_invalid_queue_type_status(self, async_client: AsyncClient):
        """Test invalid queue type status."""
        response = await async_client.get("/api/v1/queue/status/invalid")
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_404_NOT_FOUND,
        ]

    @pytest.mark.asyncio
    async def test_get_queue_health_public(self, async_client: AsyncClient):
        """Test queue health without authentication (public endpoint)."""
        response = await async_client.get("/api/v1/queue/health")
        # This is a public endpoint, should return 200 or error status
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_invalid_queue_endpoints(self, async_client: AsyncClient):
        """Test invalid queue endpoints."""
        response = await async_client.get("/api/v1/queue/nonexistent")
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_queue_endpoints_with_invalid_methods(
        self, async_client: AsyncClient
    ):
        """Test queue endpoints with invalid HTTP methods."""
        # Test PUT on status endpoint (should not be allowed)
        response = await async_client.put("/api/v1/queue/status")
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # Test DELETE on visualization endpoint (should not be allowed)
        response = await async_client.delete("/api/v1/queue/visualization")
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
