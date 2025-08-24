"""Tests for Appeals API moderator/admin endpoints."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.appeals import get_appeal_service
from therobotoverlord_api.api.appeals import router as appeals_router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_moderator
from therobotoverlord_api.database.models.appeal import AppealDecision
from therobotoverlord_api.database.models.appeal import AppealResponse
from therobotoverlord_api.database.models.appeal import AppealStats
from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal import AppealType
from therobotoverlord_api.database.models.appeal import AppealWithContent
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User


class TestAppealsModeratorAPI:
    """Test cases for Appeals API moderator/admin endpoints."""

    @pytest.fixture
    def test_app(self):
        """Create test FastAPI app without authentication middleware."""
        app = FastAPI()
        app.include_router(appeals_router, prefix="/api/v1")
        return app

    @pytest.fixture
    def client(self, test_app):
        """Create test client with test app."""
        return TestClient(test_app)

    @pytest.fixture
    def mock_appeal_service(self):
        """Mock appeal service."""
        return AsyncMock()

    @pytest.fixture
    def moderator_user(self):
        """Mock moderator user."""
        return User(
            pk=uuid4(),
            email="moderator@example.com",
            google_id="google_mod_123",
            username="moderator",
            role=UserRole.MODERATOR,
            loyalty_score=100,
            is_banned=False,
            is_sanctioned=False,
            email_verified=True,
            created_at=datetime.now(UTC),
            updated_at=None,
        )

    @pytest.fixture
    def admin_user(self):
        """Mock admin user."""
        return User(
            pk=uuid4(),
            email="admin@example.com",
            google_id="google_admin_123",
            username="admin",
            role=UserRole.ADMIN,
            loyalty_score=200,
            is_banned=False,
            is_sanctioned=False,
            email_verified=True,
            created_at=datetime.now(UTC),
            updated_at=None,
        )

    @pytest.fixture
    def regular_user(self):
        """Mock regular user."""
        return User(
            pk=uuid4(),
            email="user@example.com",
            google_id="google_123",
            username="testuser",
            role=UserRole.CITIZEN,
            loyalty_score=50,
            is_banned=False,
            is_sanctioned=False,
            email_verified=True,
            created_at=datetime.now(UTC),
            updated_at=None,
        )

    @pytest.fixture
    def sample_appeal_with_content(self):
        """Sample appeal with content data."""
        return AppealWithContent(
            pk=uuid4(),
            appellant_pk=uuid4(),
            appellant_username="testuser",
            content_type=ContentType.POST,
            content_pk=uuid4(),
            appeal_type=AppealType.POST_REJECTION,
            reason="This post was incorrectly rejected.",
            evidence="The post follows all community guidelines.",
            status=AppealStatus.PENDING,
            reviewed_by=None,
            reviewer_username=None,
            review_notes=None,
            decision_reason=None,
            submitted_at=datetime.now(UTC),
            reviewed_at=None,
            created_at=datetime.now(UTC),
            updated_at=None,
            priority_score=100,
        )

    @pytest.fixture
    def sample_appeal_decision(self):
        """Sample appeal decision data."""
        return AppealDecision(
            decision_reason="After review, the original moderation decision was correct.",
            review_notes="Content violates rule 3.2 regarding inflammatory language.",
        )

    # Appeals queue endpoints
    @pytest.mark.asyncio
    async def test_get_appeals_queue_success(
        self,
        client,
        test_app,
        mock_appeal_service,
        moderator_user,
        sample_appeal_with_content,
    ):
        """Test successful retrieval of appeals queue."""
        mock_response = AppealResponse(
            appeals=[sample_appeal_with_content],
            total_count=1,
            page=1,
            page_size=50,
            has_next=False,
            has_previous=False,
        )
        mock_appeal_service.get_appeals_queue.return_value = mock_response

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.get("/api/v1/appeals/queue")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["appeals"]) == 1
        assert response.json()["total_count"] == 1
        mock_appeal_service.get_appeals_queue.assert_called_once_with(
            AppealStatus.PENDING, 1, 50
        )

    @pytest.mark.asyncio
    async def test_get_appeals_queue_with_filters(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test appeals queue with status filter and pagination."""
        mock_response = AppealResponse(
            appeals=[],
            total_count=0,
            page=2,
            page_size=25,
            has_next=False,
            has_previous=True,
        )
        mock_appeal_service.get_appeals_queue.return_value = mock_response

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.get(
            "/api/v1/appeals/queue?status=under_review&page=2&page_size=25"
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        mock_appeal_service.get_appeals_queue.assert_called_once_with(
            AppealStatus.UNDER_REVIEW, 2, 25
        )

    @pytest.mark.asyncio
    async def test_get_appeal_for_review_success(
        self,
        client,
        test_app,
        mock_appeal_service,
        moderator_user,
        sample_appeal_with_content,
    ):
        """Test successful retrieval of appeal for review."""
        mock_appeal_service.get_appeal_by_id.return_value = sample_appeal_with_content

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.get(f"/api/v1/appeals/queue/{sample_appeal_with_content.pk}")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["pk"] == str(sample_appeal_with_content.pk)

    @pytest.mark.asyncio
    async def test_get_appeal_for_review_not_found(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test retrieval of non-existent appeal for review."""
        appeal_pk = uuid4()
        mock_appeal_service.get_appeal_by_id.return_value = None

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.get(f"/api/v1/appeals/queue/{appeal_pk}")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Appeal not found"

    @pytest.mark.asyncio
    async def test_assign_appeal_for_review_success(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test successful appeal assignment for review."""
        appeal_pk = uuid4()
        mock_appeal_service.assign_appeal_for_review.return_value = (True, "")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.patch(f"/api/v1/appeals/queue/{appeal_pk}/assign")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Appeal assigned for review"
        mock_appeal_service.assign_appeal_for_review.assert_called_once_with(
            appeal_pk, moderator_user.pk
        )

    @pytest.mark.asyncio
    async def test_assign_appeal_for_review_failure(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test failed appeal assignment for review."""
        appeal_pk = uuid4()
        mock_appeal_service.assign_appeal_for_review.return_value = (
            False,
            "Appeal already assigned to another reviewer",
        )

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.patch(f"/api/v1/appeals/queue/{appeal_pk}/assign")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            response.json()["detail"] == "Appeal already assigned to another reviewer"
        )

    # Appeal decision endpoints
    @pytest.mark.asyncio
    async def test_sustain_appeal_success(
        self,
        client,
        test_app,
        mock_appeal_service,
        moderator_user,
        sample_appeal_decision,
    ):
        """Test successful appeal sustainment."""
        appeal_pk = uuid4()
        mock_appeal_service.decide_appeal.return_value = (True, "")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/sustain",
            json={
                "decision_reason": sample_appeal_decision.decision_reason,
                "review_notes": sample_appeal_decision.review_notes,
            },
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Appeal sustained successfully"
        mock_appeal_service.decide_appeal.assert_called_once_with(
            appeal_pk, moderator_user.pk, AppealStatus.SUSTAINED, sample_appeal_decision
        )

    @pytest.mark.asyncio
    async def test_sustain_appeal_failure(
        self,
        client,
        test_app,
        mock_appeal_service,
        moderator_user,
        sample_appeal_decision,
    ):
        """Test failed appeal sustainment."""
        appeal_pk = uuid4()
        mock_appeal_service.decide_appeal.return_value = (False, "Appeal not found")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/sustain",
            json={
                "decision_reason": sample_appeal_decision.decision_reason,
                "review_notes": sample_appeal_decision.review_notes,
            },
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Appeal not found"

    @pytest.mark.asyncio
    async def test_deny_appeal_success(
        self,
        client,
        test_app,
        mock_appeal_service,
        moderator_user,
        sample_appeal_decision,
    ):
        """Test successful appeal denial."""
        appeal_pk = uuid4()
        mock_appeal_service.decide_appeal.return_value = (True, "")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/deny",
            json={
                "decision_reason": sample_appeal_decision.decision_reason,
                "review_notes": sample_appeal_decision.review_notes,
            },
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Appeal denied successfully"
        mock_appeal_service.decide_appeal.assert_called_once_with(
            appeal_pk, moderator_user.pk, AppealStatus.DENIED, sample_appeal_decision
        )

    @pytest.mark.asyncio
    async def test_deny_appeal_failure(
        self,
        client,
        test_app,
        mock_appeal_service,
        moderator_user,
        sample_appeal_decision,
    ):
        """Test failed appeal denial."""
        appeal_pk = uuid4()
        mock_appeal_service.decide_appeal.return_value = (
            False,
            "You are not assigned to review this appeal",
        )

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/deny",
            json={
                "decision_reason": sample_appeal_decision.decision_reason,
                "review_notes": sample_appeal_decision.review_notes,
            },
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "You are not assigned to review this appeal"

    # Statistics endpoint
    @pytest.mark.asyncio
    async def test_get_appeal_statistics_success(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test successful appeal statistics retrieval."""
        mock_stats = AppealStats(
            total_pending=10,
            total_under_review=5,
            total_sustained=15,
            total_denied=20,
            total_withdrawn=3,
            total_today=8,
            total_count=53,
            sustained_count=15,
            denied_count=20,
            average_review_time_hours=24.5,
            appeals_by_type={"post_rejection": 25, "topic_rejection": 15},
            top_appellants=[{"username": "user1", "appeal_count": 5}],
            reviewer_stats=[{"username": "mod1", "reviews_completed": 10}],
        )
        mock_appeal_service.get_appeal_statistics.return_value = mock_stats

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.get("/api/v1/appeals/stats")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total_pending"] == 10
        assert response.json()["total_sustained"] == 15
        assert response.json()["average_review_time_hours"] == 24.5

    # Admin-specific endpoints
    @pytest.mark.asyncio
    async def test_get_user_appeals_admin_success(
        self,
        client,
        test_app,
        mock_appeal_service,
        admin_user,
        sample_appeal_with_content,
    ):
        """Test successful retrieval of user appeals by admin."""
        user_pk = uuid4()
        mock_response = AppealResponse(
            appeals=[sample_appeal_with_content],
            total_count=1,
            page=1,
            page_size=20,
            has_next=False,
            has_previous=False,
        )
        mock_appeal_service.get_user_appeals.return_value = mock_response

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: admin_user
        test_app.dependency_overrides[require_moderator] = lambda: admin_user

        response = client.get(f"/api/v1/appeals/user/{user_pk}/appeals")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["appeals"]) == 1
        mock_appeal_service.get_user_appeals.assert_called_once_with(
            user_pk, None, 1, 20
        )

    @pytest.mark.asyncio
    async def test_get_user_appeals_admin_with_filters(
        self, client, test_app, mock_appeal_service, admin_user
    ):
        """Test retrieval of user appeals by admin with filters."""
        user_pk = uuid4()
        mock_response = AppealResponse(
            appeals=[],
            total_count=0,
            page=2,
            page_size=10,
            has_next=False,
            has_previous=True,
        )
        mock_appeal_service.get_user_appeals.return_value = mock_response

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: admin_user
        test_app.dependency_overrides[require_moderator] = lambda: admin_user

        response = client.get(
            f"/api/v1/appeals/user/{user_pk}/appeals?status=sustained&page=2&page_size=10"
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        mock_appeal_service.get_user_appeals.assert_called_once_with(
            user_pk, AppealStatus.SUSTAINED, 2, 10
        )

    # Authorization tests
    @pytest.mark.asyncio
    async def test_unauthorized_access_to_moderator_endpoints(self, client):
        """Test unauthorized access to moderator endpoints."""
        appeal_pk = uuid4()
        user_pk = uuid4()

        # Test appeals queue endpoint
        response = client.get("/api/v1/appeals/queue")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test specific appeal for review endpoint
        response = client.get(f"/api/v1/appeals/queue/{appeal_pk}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test assign appeal endpoint
        response = client.patch(f"/api/v1/appeals/queue/{appeal_pk}/assign")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test sustain appeal endpoint
        response = client.patch(f"/api/v1/appeals/queue/{appeal_pk}/sustain", json={})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test deny appeal endpoint
        response = client.patch(f"/api/v1/appeals/queue/{appeal_pk}/deny", json={})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test statistics endpoint
        response = client.get("/api/v1/appeals/stats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test user appeals admin endpoint
        response = client.get(f"/api/v1/appeals/user/{user_pk}/appeals")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_regular_user_access_to_moderator_endpoints(
        self, client, test_app, regular_user
    ):
        """Test regular user access to moderator endpoints (should be forbidden)."""
        appeal_pk = uuid4()
        user_pk = uuid4()

        test_app.dependency_overrides[get_current_user] = lambda: regular_user
        # Note: require_moderator would normally reject this, but we're testing the endpoint behavior

        # Test appeals queue endpoint
        response = client.get("/api/v1/appeals/queue")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Test specific appeal for review endpoint
        response = client.get(f"/api/v1/appeals/queue/{appeal_pk}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invalid_request_bodies(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test endpoints with invalid request bodies."""
        appeal_pk = uuid4()

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        # Test sustain appeal with missing required fields
        response = client.patch(f"/api/v1/appeals/queue/{appeal_pk}/sustain", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test deny appeal with invalid data types
        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/deny",
            json={"decision_reason": 123, "review_notes": True},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_queue_pagination_edge_cases(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test appeals queue pagination edge cases."""
        mock_response = AppealResponse(
            appeals=[],
            total_count=0,
            page=1,
            page_size=50,
            has_next=False,
            has_previous=False,
        )
        mock_appeal_service.get_appeals_queue.return_value = mock_response

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        # Test invalid page number
        response = client.get("/api/v1/appeals/queue?page=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid page size
        response = client.get("/api/v1/appeals/queue?page_size=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test page size too large
        response = client.get("/api/v1/appeals/queue?page_size=101")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invalid_appeal_status_filter(self, client, test_app, moderator_user):
        """Test appeals queue with invalid status filter."""
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        # Test with invalid status
        response = client.get("/api/v1/appeals/queue?status=invalid_status")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()
