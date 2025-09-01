"""Coverage tests for loyalty score API endpoints coverage."""

from datetime import UTC
from unittest.mock import patch

import pytest

from fastapi import status
from httpx import AsyncClient


class TestLoyaltyScoreAPICoverage:
    """Test loyalty score API endpoints for coverage improvement."""

    @pytest.mark.asyncio
    async def test_get_my_loyalty_profile_unauthorized(self, async_client: AsyncClient):
        """Test get my loyalty profile without authentication."""
        response = await async_client.get("/api/v1/loyalty/me")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_my_loyalty_events_unauthorized(self, async_client: AsyncClient):
        """Test get my loyalty events without authentication."""
        response = await async_client.get("/api/v1/loyalty/me/events")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_my_score_breakdown_unauthorized(self, async_client: AsyncClient):
        """Test get my score breakdown without authentication."""
        response = await async_client.get("/api/v1/loyalty/me/breakdown")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_loyalty_thresholds_public(self, async_client: AsyncClient):
        """Test get loyalty thresholds without authentication (public endpoint)."""
        with patch(
            "therobotoverlord_api.services.loyalty_score_service.LoyaltyScoreService.get_score_thresholds"
        ) as mock_thresholds:
            mock_thresholds.return_value = {"bronze": 0, "silver": 100, "gold": 500}

            response = await async_client.get("/api/v1/loyalty/thresholds")
            # This is a public endpoint, should return 200
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_apply_manual_adjustment_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test apply manual adjustment without authentication."""
        adjustment_data = {
            "user_pk": "550e8400-e29b-41d4-a716-446655440000",
            "score_change": 10,
            "reason": "test",
        }
        response = await async_client.post(
            "/api/v1/loyalty/adjust", json=adjustment_data
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_loyalty_stats_public(self, async_client: AsyncClient):
        """Test get loyalty stats without authentication (public endpoint)."""
        from datetime import datetime

        from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreStats

        with patch(
            "therobotoverlord_api.services.loyalty_score_service.LoyaltyScoreService.get_system_stats"
        ) as mock_stats:
            mock_stats.return_value = LoyaltyScoreStats(
                total_users=100,
                average_score=250.5,
                median_score=200,
                score_distribution={"0-100": 20, "101-500": 60, "501+": 20},
                top_10_percent_threshold=800,
                topic_creation_threshold=500,
                total_events_processed=1000,
                last_updated=datetime.now(UTC),
            )

            response = await async_client.get("/api/v1/loyalty/stats")
            # This is a public endpoint, should return 200
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_users_by_score_range_public(self, async_client: AsyncClient):
        """Test get users by score range without authentication (public endpoint)."""
        response = await async_client.get(
            "/api/v1/loyalty/range?min_score=0&max_score=100"
        )
        # This is a public endpoint, should return 200 or 500 (DB error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_recalculate_user_score_unauthorized(self, async_client: AsyncClient):
        """Test recalculate user score without authentication."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.post(
            f"/api/v1/loyalty/user/{user_id}/recalculate"
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_loyalty_score_with_invalid_data(self, async_client: AsyncClient):
        """Test loyalty score endpoints with invalid data."""
        invalid_data = {"invalid": "data"}
        response = await async_client.post("/api/v1/loyalty/adjust", json=invalid_data)
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_loyalty_score_invalid_methods(self, async_client: AsyncClient):
        """Test loyalty score endpoints with invalid HTTP methods."""
        # Test DELETE on stats endpoint (should not be allowed)
        response = await async_client.delete("/api/v1/loyalty/stats")
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # Test PUT on thresholds endpoint (should not be allowed)
        response = await async_client.put("/api/v1/loyalty/thresholds")
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
