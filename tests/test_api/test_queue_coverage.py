"""Coverage tests for queue API endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient


class TestQueueAPICoverage:
    """Test queue API endpoints for coverage improvement."""

    @pytest.mark.asyncio
    async def test_get_queue_status_unauthorized(self, async_client: AsyncClient):
        """Test queue status without authentication."""
        response = await async_client.get("/api/v1/queue/status")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_queue_position_unauthorized(self, async_client: AsyncClient):
        """Test queue position without authentication."""
        response = await async_client.get("/api/v1/queue/position")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_queue_stats_unauthorized(self, async_client: AsyncClient):
        """Test queue stats without authentication."""
        response = await async_client.get("/api/v1/queue/stats")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_process_queue_unauthorized(self, async_client: AsyncClient):
        """Test process queue without authentication."""
        response = await async_client.post("/api/v1/queue/process")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_clear_queue_unauthorized(self, async_client: AsyncClient):
        """Test clear queue without authentication."""
        response = await async_client.delete("/api/v1/queue/clear")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_queue_health_unauthorized(self, async_client: AsyncClient):
        """Test queue health without authentication."""
        response = await async_client.get("/api/v1/queue/health")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_invalid_queue_endpoints(self, async_client: AsyncClient):
        """Test invalid queue endpoints."""
        response = await async_client.get("/api/v1/queue/nonexistent")
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    @pytest.mark.asyncio
    async def test_queue_endpoints_with_invalid_methods(self, async_client: AsyncClient):
        """Test queue endpoints with invalid HTTP methods."""
        # Test PUT on status endpoint (should not be allowed)
        response = await async_client.put("/api/v1/queue/status")
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

        # Test DELETE on position endpoint (should not be allowed)
        response = await async_client.delete("/api/v1/queue/position")
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
