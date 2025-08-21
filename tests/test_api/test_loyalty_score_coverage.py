"""Coverage tests for loyalty score API endpoints."""

import pytest

from fastapi import status
from httpx import AsyncClient


class TestLoyaltyScoreAPICoverage:
    """Test loyalty score API endpoints for coverage improvement."""

    @pytest.mark.asyncio
    async def test_get_user_loyalty_score_unauthorized(self, async_client: AsyncClient):
        """Test get user loyalty score without authentication."""
        response = await async_client.get("/api/v1/loyalty-score")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_loyalty_history_unauthorized(self, async_client: AsyncClient):
        """Test get loyalty history without authentication."""
        response = await async_client.get("/api/v1/loyalty-score/history")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_loyalty_breakdown_unauthorized(self, async_client: AsyncClient):
        """Test get loyalty breakdown without authentication."""
        response = await async_client.get("/api/v1/loyalty-score/breakdown")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_loyalty_thresholds_unauthorized(self, async_client: AsyncClient):
        """Test get loyalty thresholds without authentication."""
        response = await async_client.get("/api/v1/loyalty-score/thresholds")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_update_loyalty_score_unauthorized(self, async_client: AsyncClient):
        """Test update loyalty score without authentication."""
        update_data = {"score_change": 10, "reason": "test"}
        response = await async_client.post(
            "/api/v1/loyalty-score/update", json=update_data
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_loyalty_stats_unauthorized(self, async_client: AsyncClient):
        """Test get loyalty stats without authentication."""
        response = await async_client.get("/api/v1/loyalty-score/stats")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_loyalty_predictions_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test get loyalty predictions without authentication."""
        response = await async_client.get("/api/v1/loyalty-score/predictions")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_bulk_update_loyalty_unauthorized(self, async_client: AsyncClient):
        """Test bulk update loyalty scores without authentication."""
        bulk_data = {"updates": [{"user_id": "test", "change": 5}]}
        response = await async_client.post(
            "/api/v1/loyalty-score/bulk-update", json=bulk_data
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_loyalty_score_with_invalid_data(self, async_client: AsyncClient):
        """Test loyalty score endpoints with invalid data."""
        invalid_data = {"invalid": "data"}
        response = await async_client.post(
            "/api/v1/loyalty-score/update", json=invalid_data
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_loyalty_score_invalid_methods(self, async_client: AsyncClient):
        """Test loyalty score endpoints with invalid HTTP methods."""
        # Test DELETE on score endpoint (should not be allowed)
        response = await async_client.delete("/api/v1/loyalty-score")
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # Test PUT on history endpoint (should not be allowed)
        response = await async_client.put("/api/v1/loyalty-score/history")
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
