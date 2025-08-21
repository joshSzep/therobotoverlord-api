"""Comprehensive tests for queue API endpoints."""

from datetime import UTC
from datetime import datetime
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.queue import router as queue_router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User


@pytest.fixture
def test_app():
    """Create test FastAPI app without middleware."""
    app = FastAPI()
    app.include_router(queue_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    # Create mock user with all required fields
    user_data = {
        "pk": uuid4(),
        "id": uuid4(),
        "email": "test@example.com",
        "google_id": "google123",
        "username": "testuser",
        "display_name": "Test User",
        "role": UserRole.CITIZEN,
        "loyalty_score": 50,
        "is_banned": False,
        "is_sanctioned": False,
        "email_verified": True,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    return User.model_validate(user_data)


class TestQueueAPIComprehensive:
    """Comprehensive test coverage for queue API endpoints."""

    def test_get_overall_queue_status_success(self, client, test_app):
        """Test successful overall queue status retrieval."""
        mock_queue_service = AsyncMock()
        mock_queue_service.get_queue_status.side_effect = [
            {"total": 5, "processing": 1, "pending": 4},  # topics
            {"total": 3, "processing": 0, "pending": 3},  # posts
            {"total": 2, "processing": 1, "pending": 1},  # messages
        ]

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data
        assert "topics" in data["data"]
        assert "posts" in data["data"]
        assert "messages" in data["data"]
        assert data["data"]["system_status"] == "operational"

    def test_get_queue_type_status_topics_success(self, client, test_app):
        """Test successful queue status for topics."""
        mock_queue_service = AsyncMock()
        mock_queue_service.get_queue_status.return_value = {
            "total": 10,
            "processing": 2,
            "pending": 8,
            "average_wait_time": "5 minutes",
        }

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/status/topics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["total"] == 10
        assert data["data"]["processing"] == 2
        assert data["data"]["pending"] == 8

    def test_get_queue_type_status_posts_success(self, client, test_app):
        """Test successful queue status for posts."""
        mock_queue_service = AsyncMock()
        mock_queue_service.get_queue_status.return_value = {
            "total": 5,
            "processing": 1,
            "pending": 4,
        }

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/status/posts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["total"] == 5

    def test_get_queue_type_status_messages_success(self, client, test_app):
        """Test successful queue status for messages."""
        mock_queue_service = AsyncMock()
        mock_queue_service.get_queue_status.return_value = {
            "total": 0,
            "processing": 0,
            "pending": 0,
        }

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/status/messages")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["total"] == 0

    def test_get_queue_type_status_invalid_type(self, client, test_app):
        """Test queue status with invalid queue type."""
        response = client.get("/api/v1/queue/status/invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_queue_type_status_with_error(self, client, test_app):
        """Test queue status when service returns error."""
        mock_queue_service = AsyncMock()
        mock_queue_service.get_queue_status.return_value = {
            "error": "Database connection failed"
        }

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/status/topics")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Database connection failed" in data["detail"]

    def test_get_content_queue_position_success(self, client, test_app, mock_user):
        """Test successful content queue position retrieval."""
        content_id = uuid4()
        mock_queue_service = AsyncMock()
        mock_queue_service.get_content_position.return_value = {
            "position": 3,
            "estimated_wait_time": "10 minutes",
            "status": "pending",
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get(f"/api/v1/queue/position/topics/{content_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["position"] == 3
        assert data["data"]["estimated_wait_time"] == "10 minutes"

    def test_get_content_queue_position_not_found(self, client, test_app, mock_user):
        """Test content queue position when content not found."""
        content_id = uuid4()
        mock_queue_service = AsyncMock()
        mock_queue_service.get_content_position.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get(f"/api/v1/queue/position/posts/{content_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Content not found in queue" in data["detail"]

    def test_get_content_queue_position_invalid_content_type(
        self, client, test_app, mock_user
    ):
        """Test content queue position with invalid content type."""
        content_id = uuid4()

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        response = client.get(f"/api/v1/queue/position/invalid/{content_id}")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_content_queue_position_invalid_uuid(self, client, test_app, mock_user):
        """Test content queue position with invalid UUID."""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        response = client.get("/api/v1/queue/position/topics/invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_queue_visualization_data_success(self, client, test_app):
        """Test successful queue visualization data retrieval."""
        mock_queue_service = AsyncMock()
        mock_queue_service._ensure_connections = AsyncMock()

        # Create sample data matching the database schema expected by the API
        sample_data = [
            {
                "content_type": "topic",
                "content_id": uuid4(),
                "position_in_queue": 1,
                "status": "pending",
                "entered_queue_at": datetime.now(UTC),
                "estimated_completion_at": datetime.now(UTC),
            }
        ]

        # Mock database connection and fetch
        mock_db = AsyncMock()
        mock_db.fetch.return_value = sample_data
        mock_queue_service.db = mock_db

        # Mock queue status calls
        mock_queue_service.get_queue_status.side_effect = [
            {"total": 5, "pending": 4, "processing": 1},  # topics
            {"total": 3, "pending": 2, "processing": 1},  # posts
        ]

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/visualization")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert "recent_activity" in data["data"]
        assert "queue_stats" in data["data"]
        assert len(data["data"]["recent_activity"]) == 1
        assert data["data"]["recent_activity"][0]["content_type"] == "topic"
        assert data["data"]["queue_stats"]["topics"]["total"] == 5

    def test_get_queue_visualization_data_with_limit(self, client, test_app):
        """Test queue visualization data with custom limit."""
        mock_queue_service = AsyncMock()
        mock_queue_service._ensure_connections = AsyncMock()
        mock_queue_service.db.fetch.return_value = []
        mock_queue_service.get_queue_status.side_effect = [{"total": 0}, {"total": 0}]

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/visualization?limit=10")

        assert response.status_code == status.HTTP_200_OK
        # Verify the limit was passed to the database query
        mock_queue_service.db.fetch.assert_called_once_with(ANY, 10)

    def test_get_queue_visualization_data_invalid_limit(self, client, test_app):
        """Test queue visualization data with invalid limit."""
        # Test limit too high
        response = client.get("/api/v1/queue/visualization?limit=100")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test limit too low
        response = client.get("/api/v1/queue/visualization?limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_queue_visualization_data_database_error(self, client, test_app):
        """Test queue visualization data when database fails."""
        mock_queue_service = AsyncMock()
        mock_queue_service._ensure_connections = AsyncMock()
        mock_queue_service.db.fetch.side_effect = Exception(
            "Database connection failed"
        )

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/visualization")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to get visualization data" in data["detail"]

    def test_get_queue_health_all_healthy(self, client, test_app):
        """Test queue health when all systems are healthy."""
        mock_queue_service = AsyncMock()
        mock_queue_service._ensure_connections = AsyncMock()
        mock_queue_service.db.fetchval.return_value = 1

        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            with patch(
                "therobotoverlord_api.api.queue.get_redis_client",
                return_value=mock_redis_client,
            ):
                response = client.get("/api/v1/queue/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["database"]["healthy"] is True
        assert data["data"]["redis"]["healthy"] is True
        assert "workers" in data["data"]

    def test_get_queue_health_redis_unhealthy(self, client, test_app):
        """Test queue health when Redis is unhealthy."""
        mock_queue_service = AsyncMock()
        mock_queue_service._ensure_connections = AsyncMock()
        mock_queue_service.db.fetchval.return_value = 1

        mock_redis_client = AsyncMock()
        mock_redis_client.ping.side_effect = Exception("Redis connection failed")

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            with patch(
                "therobotoverlord_api.api.queue.get_redis_client",
                return_value=mock_redis_client,
            ):
                response = client.get("/api/v1/queue/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "degraded"
        assert data["data"]["database"]["healthy"] is True
        assert data["data"]["redis"]["healthy"] is False

    def test_get_queue_health_database_unhealthy(self, client, test_app):
        """Test queue health when database is unhealthy."""
        mock_queue_service = AsyncMock()
        mock_queue_service._ensure_connections = AsyncMock()
        mock_queue_service.db.fetchval.return_value = 0  # Database unhealthy

        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            with patch(
                "therobotoverlord_api.api.queue.get_redis_client",
                return_value=mock_redis_client,
            ):
                response = client.get("/api/v1/queue/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "degraded"
        assert data["data"]["database"]["healthy"] is False
        assert data["data"]["redis"]["healthy"] is True

    def test_get_queue_health_all_unhealthy(self, client, test_app):
        """Test queue health when all systems are unhealthy."""
        mock_queue_service = AsyncMock()
        mock_queue_service._ensure_connections = AsyncMock()
        mock_queue_service.db.fetchval.return_value = 0

        mock_redis_client = AsyncMock()
        mock_redis_client.ping.side_effect = Exception("Redis failed")

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            with patch(
                "therobotoverlord_api.api.queue.get_redis_client",
                return_value=mock_redis_client,
            ):
                response = client.get("/api/v1/queue/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "degraded"
        assert data["data"]["database"]["healthy"] is False
        assert data["data"]["redis"]["healthy"] is False

    def test_get_queue_health_exception_handling(self, client, test_app):
        """Test queue health when an exception occurs."""
        mock_queue_service = AsyncMock()
        mock_queue_service._ensure_connections.side_effect = Exception(
            "Connection failed"
        )

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert data["data"]["error"] == "Queue system health check failed"
        assert data["data"]["database"]["healthy"] is False
        assert data["data"]["redis"]["healthy"] is False

    def test_queue_endpoints_without_authentication(self, client, test_app):
        """Test that public endpoints work without authentication."""
        # Test that status endpoints don't require authentication
        mock_queue_service = AsyncMock()
        mock_queue_service.get_queue_status.return_value = {
            "total": 0,
            "pending": 0,
            "processing": 0,
        }

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/status")
            assert response.status_code == status.HTTP_200_OK

            response = client.get("/api/v1/queue/status/topics")
            assert response.status_code == status.HTTP_200_OK

    def test_get_content_queue_position_all_content_types(
        self, client, test_app, mock_user
    ):
        """Test content queue position for all valid content types."""
        content_id = uuid4()
        mock_queue_service = AsyncMock()
        mock_queue_service.get_content_position.return_value = {
            "position": 1,
            "status": "pending",
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            # Test topics
            response = client.get(f"/api/v1/queue/position/topics/{content_id}")
            assert response.status_code == status.HTTP_200_OK

            # Test posts
            response = client.get(f"/api/v1/queue/position/posts/{content_id}")
            assert response.status_code == status.HTTP_200_OK

            # Test messages
            response = client.get(f"/api/v1/queue/position/messages/{content_id}")
            assert response.status_code == status.HTTP_200_OK

    def test_get_queue_visualization_empty_results(self, client, test_app):
        """Test queue visualization with empty database results."""
        mock_queue_service = AsyncMock()
        mock_queue_service._ensure_connections = AsyncMock()
        mock_queue_service.db.fetch.return_value = []  # Empty results
        mock_queue_service.get_queue_status.side_effect = [
            {"total": 0, "pending": 0, "processing": 0},
            {"total": 0, "pending": 0, "processing": 0},
        ]

        with patch(
            "therobotoverlord_api.api.queue.get_queue_service",
            return_value=mock_queue_service,
        ):
            response = client.get("/api/v1/queue/visualization")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["recent_activity"] == []
        assert "queue_stats" in data["data"]
