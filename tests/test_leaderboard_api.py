"""Unit tests for leaderboard API endpoints."""

import json

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.leaderboard import router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import get_optional_user
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.leaderboard import LeaderboardEntry
from therobotoverlord_api.database.models.leaderboard import LeaderboardFilters
from therobotoverlord_api.database.models.leaderboard import LeaderboardSearchResult
from therobotoverlord_api.database.models.leaderboard import PersonalLeaderboardStats
from therobotoverlord_api.database.models.leaderboard import UserRankLookup
from therobotoverlord_api.main import app

pytest_plugins = ["tests.fixtures.leaderboard_fixtures"]


class TestLeaderboardAPI:
    """Test leaderboard API endpoints with mocked service."""

    @pytest.fixture
    def mock_leaderboard_service(self):
        """Mock leaderboard service for testing."""
        return AsyncMock()

    @pytest.fixture
    def mock_current_user(self):
        """Mock current user for authenticated endpoints."""
        user = AsyncMock()
        user.pk = uuid4()
        user.username = "test_user"
        user.role = UserRole.CITIZEN
        return user

    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user for admin endpoints."""
        user = AsyncMock()
        user.pk = uuid4()
        user.username = "admin_user"
        user.email = "admin@example.com"
        user.role = UserRole.ADMIN
        return user

    @pytest.fixture
    def client(self, mock_current_user):
        """Create test client."""

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        # Override the get_optional_user dependency to return our mock user
        app.dependency_overrides[get_optional_user] = lambda: mock_current_user

        return TestClient(app)

    @pytest.fixture
    def client_with_admin_auth(self, mock_admin_user):
        """Test client with admin authentication."""

        # Store original overrides
        original_overrides = app.dependency_overrides.copy()

        # Set admin user override
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        try:
            yield TestClient(app)
        finally:
            # Restore original overrides
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    @pytest.mark.asyncio
    async def test_get_leaderboard_success(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_response,
        mock_current_user,
    ):
        """Test successful leaderboard retrieval."""
        # Mock service response
        mock_response = sample_leaderboard_response
        mock_leaderboard_service.get_leaderboard.return_value = mock_response

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get("/api/v1/leaderboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["entries"]) == 5
        assert data["pagination"]["has_next"] is False
        assert data["total_users"] == 100

        # Verify service was called with defaults
        expected_filters = LeaderboardFilters(
            badge_name=None,
            min_loyalty_score=None,
            max_loyalty_score=None,
            min_rank=None,
            max_rank=None,
            username_search=None,
            topic_creators_only=False,
            active_users_only=True,
        )
        # Should be called with the mock user's PK since we have an authenticated client
        mock_leaderboard_service.get_leaderboard.assert_called_once_with(
            limit=50,
            cursor=None,
            filters=expected_filters,
            current_user_pk=mock_current_user.pk,
        )

    @pytest.mark.asyncio
    async def test_get_leaderboard_with_parameters(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_response,
    ):
        """Test leaderboard retrieval with query parameters."""
        # Mock service response
        mock_response = sample_leaderboard_response
        mock_leaderboard_service.get_leaderboard.return_value = mock_response

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get(
                "/api/v1/leaderboard",
                params={
                    "limit": 3,
                    "badge_name": "Logic Master",
                    "min_loyalty_score": 50,
                    "max_loyalty_score": 200,
                    "username_search": "citizen",
                    "topic_creators_only": True,
                    "active_users_only": False,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["entries"]) == 5
        assert data["pagination"]["has_next"] is False
        assert data["total_users"] == 100

        # Verify service was called with filters
        call_args = mock_leaderboard_service.get_leaderboard.call_args
        assert call_args.kwargs["limit"] == 3
        filters = call_args.kwargs["filters"]
        assert filters.badge_name == "Logic Master"
        assert filters.min_loyalty_score == 50
        assert filters.max_loyalty_score == 200
        assert filters.username_search == "citizen"
        assert filters.topic_creators_only is True
        assert filters.active_users_only is False

    @pytest.mark.asyncio
    async def test_get_leaderboard_with_cursor(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_response,
    ):
        """Test leaderboard retrieval with cursor pagination."""
        cursor_data = {
            "rank": 10,
            "user_pk": str(uuid4()),
            "loyalty_score": 100,
        }

        mock_leaderboard_service.get_leaderboard.return_value = (
            sample_leaderboard_response
        )

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get(
                "/api/v1/leaderboard",
                params={"cursor": json.dumps(cursor_data)},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["entries"]) == 5
        assert data["pagination"]["has_next"] is False
        assert data["total_users"] == 100

    @pytest.mark.asyncio
    async def test_get_leaderboard_with_current_user(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_response,
        sample_user,
    ):
        """Test leaderboard retrieval with current user highlighting."""
        mock_leaderboard_service.get_leaderboard.return_value = (
            sample_leaderboard_response
        )

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get("/api/v1/leaderboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["entries"]) == 5
        assert data["pagination"]["has_next"] is False
        assert data["total_users"] == 100

    @pytest.mark.asyncio
    async def test_get_leaderboard_invalid_cursor(
        self, client, mock_leaderboard_service
    ):
        """Test leaderboard retrieval with invalid cursor."""
        # Mock service to raise ValueError for invalid cursor
        mock_leaderboard_service.get_leaderboard.side_effect = ValueError(
            "Invalid cursor format"
        )

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get(
                "/api/v1/leaderboard",
                params={"cursor": "invalid_json"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid cursor format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_top_users_success(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_entries,
    ):
        """Test successful top users retrieval."""
        mock_leaderboard_service.get_top_users.return_value = (
            sample_leaderboard_entries[:10]
        )

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get("/api/v1/leaderboard/top/10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 10
        assert data["data"][0]["rank"] == 1

        # Verify service was called with count parameter
        mock_leaderboard_service.get_top_users.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_get_top_users_with_limit(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_entries,
    ):
        """Test top users retrieval with custom limit."""
        mock_leaderboard_service.get_top_users.return_value = (
            sample_leaderboard_entries[:5]
        )

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get("/api/v1/leaderboard/top/5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 5

        mock_leaderboard_service.get_top_users.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_get_leaderboard_stats_success(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_stats,
    ):
        """Test successful leaderboard stats retrieval."""
        mock_leaderboard_service.get_leaderboard_stats.return_value = (
            sample_leaderboard_stats
        )

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get("/api/v1/leaderboard/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_users"] == 1000
        assert data["average_loyalty_score"] == 75.5
        assert "score_distribution" in data

        mock_leaderboard_service.get_leaderboard_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_users_success(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_entries,
    ):
        """Test successful user search."""
        search_results = [
            LeaderboardSearchResult(
                user_pk=entry.user_pk,
                username=entry.username,
                rank=entry.rank,
                loyalty_score=entry.loyalty_score,
                match_score=0.9,
            )
            for entry in sample_leaderboard_entries[:3]
        ]

        mock_leaderboard_service.search_users.return_value = search_results

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get(
                "/api/v1/leaderboard/search",
                params={"q": "citizen", "limit": 20},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert len(data["data"]) == 3

        mock_leaderboard_service.search_users.assert_called_once_with("citizen", 20)

    @pytest.mark.asyncio
    async def test_search_users_missing_query(self, client, mock_leaderboard_service):
        """Test user search without query parameter."""
        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get("/api/v1/leaderboard/search")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_user_rank_success(
        self,
        client,
        mock_leaderboard_service,
        sample_user_rank_lookup,
    ):
        """Test successful user rank retrieval."""
        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service"
        ) as mock_get_service:
            mock_get_service.return_value.repository.get_user_rank.return_value = (
                sample_user_rank_lookup
            )
            response = client.get(
                f"/api/v1/leaderboard/user/{sample_user_rank_lookup.user_pk}"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["found"] is True
        assert data["rank"] == 42
        assert data["username"] == "test_citizen"

        mock_get_service.return_value.repository.get_user_rank.assert_called_once_with(
            sample_user_rank_lookup.user_pk
        )

    @pytest.mark.asyncio
    async def test_get_user_rank_not_found(
        self,
        client,
        mock_leaderboard_service,
    ):
        """Test user rank retrieval for non-existent user."""
        user_pk = uuid4()
        not_found_lookup = UserRankLookup(
            user_pk=user_pk,
            username="",
            rank=0,
            loyalty_score=0,
            percentile_rank=1.0,
            found=False,
        )
        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service"
        ) as mock_get_service:
            mock_get_service.return_value.repository.get_user_rank.return_value = (
                not_found_lookup
            )
            response = client.get(f"/api/v1/leaderboard/user/{user_pk}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_user_personal_stats_success(
        self,
        client,
        mock_leaderboard_service,
        sample_user_rank_lookup,
        sample_rank_history,
        sample_leaderboard_entries,
    ):
        """Test successful user personal stats retrieval."""
        # Convert UserRankLookup to LeaderboardEntry for current_position
        current_position = LeaderboardEntry(
            user_pk=sample_user_rank_lookup.user_pk,
            username=sample_user_rank_lookup.username,
            loyalty_score=sample_user_rank_lookup.loyalty_score,
            rank=sample_user_rank_lookup.rank,
            percentile_rank=sample_user_rank_lookup.percentile_rank,
            badges=[],
            topic_creation_enabled=True,
            topics_created_count=0,
            is_current_user=True,
            created_at=sample_leaderboard_entries[0].created_at,
        )

        personal_stats = PersonalLeaderboardStats(
            current_position=current_position,
            rank_history=sample_rank_history,
            nearby_users=sample_leaderboard_entries[:5],
            achievement_progress={"loyalty_master": 0.75, "topic_creator": 0.5},
        )
        mock_leaderboard_service.get_user_personal_stats.return_value = personal_stats

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get(
                f"/api/v1/leaderboard/user/{sample_user_rank_lookup.user_pk}/stats"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "current_position" in data
        assert "rank_history" in data
        assert "nearby_users" in data
        assert "achievement_progress" in data
        assert len(data["rank_history"]) == 2
        assert len(data["nearby_users"]) == 5

    @pytest.mark.asyncio
    async def test_get_nearby_users_success(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_entries,
    ):
        """Test successful nearby users retrieval."""
        user_pk = uuid4()

        # Use first 5 entries from sample data
        nearby_users = sample_leaderboard_entries[:5]

        # Mock the repository method that's actually called
        mock_leaderboard_service.repository.get_nearby_users.return_value = nearby_users

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get(f"/api/v1/leaderboard/user/{user_pk}/nearby")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert len(data["data"]) == 5

    @pytest.mark.asyncio
    async def test_get_nearby_users_with_context_size(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_entries,
    ):
        """Test nearby users retrieval with custom context size."""
        user_pk = uuid4()

        # Use first 6 entries from sample data
        nearby_users = sample_leaderboard_entries[:6]

        # Mock the repository method that's actually called
        mock_leaderboard_service.repository.get_nearby_users.return_value = nearby_users

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get(
                f"/api/v1/leaderboard/user/{user_pk}/nearby",
                params={"context_size": 6},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert len(data["data"]) == 6

    @pytest.mark.asyncio
    async def test_get_users_by_rank_range_success(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_entries,
    ):
        """Test successful users by rank range retrieval."""
        mock_leaderboard_service.get_users_by_rank_range.return_value = (
            sample_leaderboard_entries[4:7]
        )

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get(
                "/api/v1/leaderboard/rank-range",
                params={"start_rank": 5, "end_rank": 7},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3

        mock_leaderboard_service.get_users_by_rank_range.assert_called_once_with(5, 7)

    @pytest.mark.asyncio
    async def test_get_users_by_percentile_range_success(
        self,
        client,
        mock_leaderboard_service,
        sample_leaderboard_entries,
    ):
        """Test successful users by percentile range retrieval."""
        mock_leaderboard_service.get_users_by_percentile_range.return_value = (
            sample_leaderboard_entries[:5]
        )

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client.get(
                "/api/v1/leaderboard/percentile-range",
                params={"start_percentile": 0.0, "end_percentile": 0.05},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 5

        mock_leaderboard_service.get_users_by_percentile_range.assert_called_once_with(
            0.0, 0.05
        )

    @pytest.mark.asyncio
    async def test_refresh_leaderboard_success_admin(
        self,
        client_with_admin_auth,
        mock_leaderboard_service,
        mock_admin_user,
    ):
        """Test successful leaderboard refresh by admin."""
        mock_leaderboard_service.refresh_leaderboard_data.return_value = True

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client_with_admin_auth.post("/api/v1/leaderboard/refresh")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert "refreshed successfully" in data["message"]

        mock_leaderboard_service.refresh_leaderboard_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_leaderboard_failure_admin(
        self,
        client_with_admin_auth,
        mock_leaderboard_service,
        mock_admin_user,
    ):
        """Test leaderboard refresh failure by admin."""
        mock_leaderboard_service.refresh_leaderboard_data.return_value = False

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            response = client_with_admin_auth.post("/api/v1/leaderboard/refresh")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to refresh" in data["detail"]

    @pytest.mark.asyncio
    async def test_admin_refresh_forbidden(self, mock_current_user):
        """Test admin refresh leaderboard returns 403 for non-admin users."""

        # Create a test client with non-admin user
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        # Override dependencies to return non-admin user
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides[get_optional_user] = lambda: mock_current_user

        client = TestClient(app)
        response = client.post("/api/v1/leaderboard/refresh")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_parameter_validation_limits(self, client, mock_leaderboard_service):
        """Test parameter validation for limits."""
        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            # Test limit too high
            response = client.get("/api/v1/leaderboard", params={"limit": 1001})
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test limit too low
            response = client.get("/api/v1/leaderboard", params={"limit": 0})
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_parameter_validation_scores(
        self, client, mock_leaderboard_service, sample_leaderboard_response
    ):
        """Test parameter validation for loyalty scores."""
        # Set up mock response to avoid serialization issues
        mock_leaderboard_service.get_leaderboard.return_value = (
            sample_leaderboard_response
        )

        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            # Test invalid score range
            response = client.get(
                "/api/v1/leaderboard",
                params={"min_loyalty_score": 100, "max_loyalty_score": 50},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_parameter_validation_percentiles(
        self, client, mock_leaderboard_service
    ):
        """Test parameter validation for percentiles."""
        with patch(
            "therobotoverlord_api.api.leaderboard.get_leaderboard_service",
            return_value=mock_leaderboard_service,
        ):
            # Test invalid percentile range
            response = client.get(
                "/api/v1/leaderboard/percentile-range",
                params={"start_percentile": 0.5, "end_percentile": 0.2},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test percentile out of bounds
            response = client.get(
                "/api/v1/leaderboard/percentile-range",
                params={"start_percentile": -0.1, "end_percentile": 0.5},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
