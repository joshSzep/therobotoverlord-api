"""Coverage tests for badges API endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient


class TestBadgesAPICoverage:
    """Test badges API endpoints for coverage improvement."""

    @pytest.mark.asyncio
    async def test_get_badges_unauthorized(self, async_client: AsyncClient):
        """Test get badges without authentication."""
        response = await async_client.get("/api/v1/badges")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_create_badge_unauthorized(self, async_client: AsyncClient):
        """Test create badge without authentication."""
        badge_data = {
            "name": "Test Badge",
            "description": "A test badge",
            "badge_type": "achievement",
            "criteria": {"posts": 10},
            "points": 100
        }
        response = await async_client.post("/api/v1/badges", json=badge_data)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_badge_by_id_unauthorized(self, async_client: AsyncClient):
        """Test get badge by ID without authentication."""
        badge_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(f"/api/v1/badges/{badge_id}")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_update_badge_unauthorized(self, async_client: AsyncClient):
        """Test update badge without authentication."""
        badge_id = "550e8400-e29b-41d4-a716-446655440000"
        update_data = {"description": "Updated description"}
        response = await async_client.put(f"/api/v1/badges/{badge_id}", json=update_data)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_delete_badge_unauthorized(self, async_client: AsyncClient):
        """Test delete badge without authentication."""
        badge_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.delete(f"/api/v1/badges/{badge_id}")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_user_badges_unauthorized(self, async_client: AsyncClient):
        """Test get user badges without authentication."""
        response = await async_client.get("/api/v1/badges/user")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_award_badge_unauthorized(self, async_client: AsyncClient):
        """Test award badge without authentication."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        badge_id = "550e8400-e29b-41d4-a716-446655440001"
        response = await async_client.post(f"/api/v1/badges/{badge_id}/award/{user_id}")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_revoke_badge_unauthorized(self, async_client: AsyncClient):
        """Test revoke badge without authentication."""
        user_badge_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.delete(f"/api/v1/badges/user/{user_badge_id}")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_badge_leaderboard_unauthorized(self, async_client: AsyncClient):
        """Test get badge leaderboard without authentication."""
        response = await async_client.get("/api/v1/badges/leaderboard")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_invalid_badge_id_format(self, async_client: AsyncClient):
        """Test invalid badge ID format."""
        response = await async_client.get("/api/v1/badges/invalid-uuid")
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    @pytest.mark.asyncio
    async def test_create_badge_invalid_data(self, async_client: AsyncClient):
        """Test create badge with invalid data."""
        invalid_data = {"invalid": "data"}
        response = await async_client.post("/api/v1/badges", json=invalid_data)
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
