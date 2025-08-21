"""Comprehensive tests for Appeals API endpoints."""

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
from therobotoverlord_api.database.models.appeal import AppealCreate
from therobotoverlord_api.database.models.appeal import AppealDecision
from therobotoverlord_api.database.models.appeal import AppealEligibility
from therobotoverlord_api.database.models.appeal import AppealResponse
from therobotoverlord_api.database.models.appeal import AppealStats
from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal import AppealType
from therobotoverlord_api.database.models.appeal import AppealWithContent
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User


class TestAppealsAPIComprehensive:
    """Comprehensive test cases for Appeals API endpoints."""

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
    def sample_appeal_create(self):
        """Sample appeal creation data."""
        return AppealCreate(
            content_type=ContentType.POST,
            content_pk=uuid4(),
            appeal_type=AppealType.POST_REJECTION,
            reason="This post was incorrectly rejected.",
            evidence="The post follows all community guidelines.",
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

    # User-facing endpoint tests
    @pytest.mark.asyncio
    async def test_submit_appeal_success(
        self, client, test_app, mock_appeal_service, regular_user, sample_appeal_create, sample_appeal_with_content
    ):
        """Test successful appeal submission."""
        mock_appeal = type("Appeal", (), {"pk": uuid4()})()
        mock_appeal_service.submit_appeal.return_value = (mock_appeal, "")
        mock_appeal_service.get_appeal_by_id.return_value = sample_appeal_with_content

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "post",
                "content_pk": str(sample_appeal_create.content_pk),
                "appeal_type": "post_rejection",
                "reason": sample_appeal_create.reason,
                "evidence": sample_appeal_create.evidence,
            },
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["pk"] == str(sample_appeal_with_content.pk)
        mock_appeal_service.submit_appeal.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_appeal_failure(
        self, client, test_app, mock_appeal_service, regular_user, sample_appeal_create
    ):
        """Test failed appeal submission."""
        mock_appeal_service.submit_appeal.return_value = (None, "Daily appeal limit reached")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "post",
                "content_pk": str(sample_appeal_create.content_pk),
                "appeal_type": "post_rejection",
                "reason": sample_appeal_create.reason,
                "evidence": sample_appeal_create.evidence,
            },
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Daily appeal limit reached"

    @pytest.mark.asyncio
    async def test_submit_appeal_creation_error(
        self, client, test_app, mock_appeal_service, regular_user, sample_appeal_create
    ):
        """Test appeal submission when creation succeeds but retrieval fails."""
        mock_appeal = type("Appeal", (), {"pk": uuid4()})()
        mock_appeal_service.submit_appeal.return_value = (mock_appeal, "")
        mock_appeal_service.get_appeal_by_id.return_value = None

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "post",
                "content_pk": str(sample_appeal_create.content_pk),
                "appeal_type": "post_rejection",
                "reason": sample_appeal_create.reason,
                "evidence": sample_appeal_create.evidence,
            },
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to retrieve created appeal"

    @pytest.mark.asyncio
    async def test_check_appeal_eligibility_success(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test successful appeal eligibility check."""
        content_pk = uuid4()
        mock_eligibility = AppealEligibility(
            eligible=True,
            appeals_remaining=2,
            max_appeals_per_day=3,
            appeals_used_today=1,
            reason=None,
        )
        mock_appeal_service.check_appeal_eligibility.return_value = mock_eligibility

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get(
            f"/api/v1/appeals/eligibility?content_type=post&content_pk={content_pk}"
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["eligible"] is True
        assert response.json()["appeals_remaining"] == 2

    @pytest.mark.asyncio
    async def test_check_appeal_eligibility_not_eligible(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test appeal eligibility check when not eligible."""
        content_pk = uuid4()
        mock_eligibility = AppealEligibility(
            eligible=False,
            appeals_remaining=0,
            max_appeals_per_day=3,
            appeals_used_today=3,
            reason="Daily appeal limit reached",
        )
        mock_appeal_service.check_appeal_eligibility.return_value = mock_eligibility

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get(
            f"/api/v1/appeals/eligibility?content_type=post&content_pk={content_pk}"
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["eligible"] is False
        assert response.json()["reason"] == "Daily appeal limit reached"

    @pytest.mark.asyncio
    async def test_get_my_appeals_success(
        self, client, test_app, mock_appeal_service, regular_user, sample_appeal_with_content
    ):
        """Test successful retrieval of user's appeals."""
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
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get("/api/v1/appeals/my-appeals")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["appeals"]) == 1
        assert response.json()["total_count"] == 1

    @pytest.mark.asyncio
    async def test_get_my_appeals_with_filters(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test retrieval of user's appeals with status filter."""
        mock_response = AppealResponse(
            appeals=[],
            total_count=0,
            page=1,
            page_size=10,
            has_next=False,
            has_previous=False,
        )
        mock_appeal_service.get_user_appeals.return_value = mock_response

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get("/api/v1/appeals/my-appeals?status=pending&page=1&page_size=10")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        mock_appeal_service.get_user_appeals.assert_called_once_with(
            regular_user.pk, AppealStatus.PENDING, 1, 10
        )

    @pytest.mark.asyncio
    async def test_get_my_appeal_success(
        self, client, test_app, mock_appeal_service, regular_user, sample_appeal_with_content
    ):
        """Test successful retrieval of specific user appeal."""
        sample_appeal_with_content.appellant_pk = regular_user.pk
        mock_appeal_service.get_appeal_by_id.return_value = sample_appeal_with_content

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get(f"/api/v1/appeals/my-appeals/{sample_appeal_with_content.pk}")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["pk"] == str(sample_appeal_with_content.pk)

    @pytest.mark.asyncio
    async def test_get_my_appeal_not_found(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test retrieval of non-existent appeal."""
        appeal_pk = uuid4()
        mock_appeal_service.get_appeal_by_id.return_value = None

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get(f"/api/v1/appeals/my-appeals/{appeal_pk}")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Appeal not found"

    @pytest.mark.asyncio
    async def test_get_my_appeal_forbidden(
        self, client, test_app, mock_appeal_service, regular_user, sample_appeal_with_content
    ):
        """Test retrieval of appeal owned by different user."""
        sample_appeal_with_content.appellant_pk = uuid4()  # Different user
        mock_appeal_service.get_appeal_by_id.return_value = sample_appeal_with_content

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get(f"/api/v1/appeals/my-appeals/{sample_appeal_with_content.pk}")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "You can only view your own appeals"

    @pytest.mark.asyncio
    async def test_withdraw_appeal_success(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test successful appeal withdrawal."""
        appeal_pk = uuid4()
        mock_appeal_service.withdraw_appeal.return_value = (True, "")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.patch(f"/api/v1/appeals/my-appeals/{appeal_pk}/withdraw")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Appeal withdrawn successfully"
        mock_appeal_service.withdraw_appeal.assert_called_once_with(appeal_pk, regular_user.pk)

    @pytest.mark.asyncio
    async def test_withdraw_appeal_failure(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test failed appeal withdrawal."""
        appeal_pk = uuid4()
        mock_appeal_service.withdraw_appeal.return_value = (False, "Cannot withdraw completed appeal")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.patch(f"/api/v1/appeals/my-appeals/{appeal_pk}/withdraw")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Cannot withdraw completed appeal"

    @pytest.mark.asyncio
    async def test_get_appealable_content_success(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test successful retrieval of appealable content."""
        content_pk = uuid4()
        mock_content = {
            "pk": str(content_pk),
            "type": "post",
            "title": "Test Post",
            "content": "Test content",
            "moderation_reason": "Inappropriate content",
        }
        mock_appeal_service.get_appealable_content.return_value = mock_content

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get(f"/api/v1/appeals/content/post/{content_pk}")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["pk"] == str(content_pk)
        assert response.json()["title"] == "Test Post"

    @pytest.mark.asyncio
    async def test_get_appealable_content_not_found(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test retrieval of non-existent or non-appealable content."""
        content_pk = uuid4()
        mock_appeal_service.get_appealable_content.return_value = None

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get(f"/api/v1/appeals/content/post/{content_pk}")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Content not found or not appealable"

    # Authentication tests
    @pytest.mark.asyncio
    async def test_unauthorized_access_to_user_endpoints(self, client):
        """Test unauthorized access to user endpoints."""
        appeal_pk = uuid4()
        content_pk = uuid4()

        # Test submit appeal endpoint
        response = client.post("/api/v1/appeals/", json={})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test eligibility check endpoint
        response = client.get(f"/api/v1/appeals/eligibility?content_type=post&content_pk={content_pk}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test my appeals endpoint
        response = client.get("/api/v1/appeals/my-appeals")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test specific appeal endpoint
        response = client.get(f"/api/v1/appeals/my-appeals/{appeal_pk}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test withdraw appeal endpoint
        response = client.patch(f"/api/v1/appeals/my-appeals/{appeal_pk}/withdraw")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test appealable content endpoint
        response = client.get(f"/api/v1/appeals/content/post/{content_pk}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_uuid_parameters(self, client, test_app, regular_user):
        """Test endpoints with invalid UUID parameters."""
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Test with invalid appeal UUID
        response = client.get("/api/v1/appeals/my-appeals/invalid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test with invalid content UUID
        response = client.get("/api/v1/appeals/content/post/invalid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invalid_content_type_parameter(self, client, test_app, regular_user):
        """Test endpoints with invalid content type parameters."""
        content_pk = uuid4()
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Test with invalid content type
        response = client.get(f"/api/v1/appeals/eligibility?content_type=invalid&content_pk={content_pk}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = client.get(f"/api/v1/appeals/content/invalid/{content_pk}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_pagination_parameters(self, client, test_app, mock_appeal_service, regular_user):
        """Test pagination parameter validation."""
        mock_response = AppealResponse(
            appeals=[],
            total_count=0,
            page=1,
            page_size=20,
            has_next=False,
            has_previous=False,
        )
        mock_appeal_service.get_user_appeals.return_value = mock_response

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Test invalid page number
        response = client.get("/api/v1/appeals/my-appeals?page=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid page size
        response = client.get("/api/v1/appeals/my-appeals?page_size=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test page size too large
        response = client.get("/api/v1/appeals/my-appeals?page_size=101")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()
