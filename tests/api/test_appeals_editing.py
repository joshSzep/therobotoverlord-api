"""Tests for Appeals API editing endpoints."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal_with_editing import (
    AppealDecisionWithEdit,
)
from therobotoverlord_api.database.models.content_version import ContentVersion
from therobotoverlord_api.database.models.content_version import ContentVersionDiff
from therobotoverlord_api.database.models.content_version import ContentVersionSummary
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.api.appeals import get_appeal_service
from therobotoverlord_api.api.appeals import get_content_versioning_service
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_moderator
from therobotoverlord_api.services.content_versioning_service import ContentVersioningService
from therobotoverlord_api.api.appeals import router as appeals_router


class TestAppealsEditingAPI:
    """Test cases for Appeals API editing endpoints."""

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
    def mock_versioning_service(self):
        """Mock content versioning service."""
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

    @pytest.mark.asyncio
    async def test_sustain_appeal_with_edit_success(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test successful appeal sustainment with editing."""
        appeal_pk = uuid4()
        decision_data = {
            "decision_reason": "Appeal is valid but content needs editing",
            "review_notes": "Fixed inappropriate language",
            "edit_content": True,
            "edited_title": "Edited Title",
            "edited_content": "Edited content",
            "edit_reason": "Removed offensive terms",
        }
        edited_content = {"title": "Edited Title", "body": "Edited content"}

        mock_appeal_service.decide_appeal_with_edit.return_value = (True, "")

        # Mock the dependencies
        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/sustain-with-edit",
            json={
                "decision_data": decision_data,
                "edited_content": edited_content,
            },
        )

        # Clean up dependency overrides
        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "message": "Appeal sustained with content restoration"
        }

        mock_appeal_service.decide_appeal_with_edit.assert_called_once_with(
            appeal_pk,
            moderator_user.pk,
            AppealStatus.SUSTAINED,
            AppealDecisionWithEdit(**decision_data),
            edited_content,
        )

    @pytest.mark.asyncio
    async def test_sustain_appeal_with_edit_failure(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test failed appeal sustainment with editing."""
        appeal_pk = uuid4()
        decision_data = {
            "decision_reason": "Appeal is valid",
            "review_notes": "Content was incorrectly flagged",
            "edit_reason": None,
        }

        mock_appeal_service.decide_appeal_with_edit.return_value = (
            False,
            "Appeal not found",
        )

        # Mock the dependencies
        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/sustain-with-edit",
            json={"decision_data": decision_data},
        )

        # Clean up dependency overrides
        test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Appeal not found"}

    @pytest.mark.asyncio
    async def test_deny_appeal_with_edit_success(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test successful appeal denial with detailed reasoning."""
        appeal_pk = uuid4()
        decision_data = {
            "decision_reason": "Appeal lacks merit and content violates guidelines",
            "review_notes": "Content violates community guidelines",
        }

        mock_appeal_service.decide_appeal_with_edit.return_value = (True, "")

        # Mock the dependencies
        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/deny-with-edit",
            json=decision_data,
        )

        # Clean up dependency overrides
        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Appeal denied"}

        mock_appeal_service.decide_appeal_with_edit.assert_called_once_with(
            appeal_pk,
            moderator_user.pk,
            AppealStatus.DENIED,
            AppealDecisionWithEdit(**decision_data),
        )

    @pytest.mark.asyncio
    async def test_get_content_version_history_success(
        self, client, test_app, mock_versioning_service, moderator_user
    ):
        """Test successful content version history retrieval."""
        content_pk = uuid4()

        mock_versions = [
            ContentVersionSummary(
                pk=uuid4(),
                content_pk=content_pk,
                content_type="post",
                version_number=1,
                editor_name="Moderator 1",
                edit_reason="Initial version",
                edit_type="appeal_restoration",
                created_at="2024-01-01T00:00:00Z",
            ),
            ContentVersionSummary(
                pk=uuid4(),
                content_pk=content_pk,
                content_type="post",
                version_number=2,
                editor_name="Moderator 2",
                edit_reason="Grammar fixes",
                edit_type="appeal_restoration",
                created_at="2024-01-02T00:00:00Z",
            ),
        ]

        mock_versioning_service.get_content_history.return_value = mock_versions

        # Mock the dependencies
        def get_versioning_service():
            return mock_versioning_service

        test_app.dependency_overrides[get_content_versioning_service] = get_versioning_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.get(f"/api/v1/appeals/content-versions/{content_pk}/history")

        # Clean up dependency overrides
        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

        mock_versioning_service.get_content_history.assert_called_once_with(content_pk)

    @pytest.mark.asyncio
    async def test_get_content_version_diff_success(
        self, client, test_app, mock_versioning_service, moderator_user
    ):
        """Test successful content version diff retrieval."""
        content_pk = uuid4()
        version_number = 2

        mock_diff = ContentVersionDiff(
            version_pk=uuid4(),
            content_pk=content_pk,
            content_type="post",
            version_number=version_number,
            previous_version=1,
            changes={
                "title": {"old": "Original", "new": "Edited"},
                "body": {"old": "Original content", "new": "Edited content"},
            },
            edit_reason="Grammar fixes",
            editor_name="Moderator 1",
        )

        mock_versioning_service.get_version_diff.return_value = mock_diff
        mock_versioning_service.get_content_history.return_value = [
            ContentVersion(
                pk=uuid4(),
                content_type="post",
                content_pk=content_pk,
                version_number=version_number,
                original_content="Original content",
                edited_content="Edited content",
                edit_reason="Grammar fixes",
                edit_type="appeal_restoration",
                created_at="2024-01-01T00:00:00Z",
            )
        ]

        def get_versioning_service():
            return mock_versioning_service
        
        test_app.dependency_overrides[get_content_versioning_service] = get_versioning_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.get(
            f"/api/v1/appeals/content-versions/{content_pk}/{version_number}/diff"
        )

        # Clean up dependency overrides
        test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["version_number"] == version_number
        assert "changes" in response.json()

        mock_versioning_service.get_content_history.assert_called_once_with(content_pk)
        mock_versioning_service.get_version_diff.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_content_version_diff_not_found(
        self, client, test_app, mock_versioning_service, moderator_user
    ):
        """Test content version diff not found."""
        content_pk = uuid4()
        version_number = 999

        mock_versioning_service.get_version_diff.return_value = None
        mock_versioning_service.get_content_history.return_value = []

        def get_versioning_service():
            return mock_versioning_service
        
        test_app.dependency_overrides[get_content_versioning_service] = get_versioning_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        response = client.get(
            f"/api/v1/appeals/content-versions/{content_pk}/{version_number}/diff"
        )

        # Clean up dependency overrides
        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Version diff not found"}

    @pytest.mark.asyncio
    async def test_unauthorized_access_to_editing_endpoints(self, client):
        """Test unauthorized access to editing endpoints."""
        appeal_pk = uuid4()
        content_pk = uuid4()

        # Test sustain with edit endpoint
        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/sustain-with-edit",
            json={"decision_reason": "Test", "review_notes": "Test"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test deny with edit endpoint
        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/deny-with-edit",
            json={"decision_reason": "Test", "review_notes": "Test"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test content history endpoint
        response = client.get(f"/api/v1/appeals/content-versions/{content_pk}/history")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test content diff endpoint
        response = client.get(f"/api/v1/appeals/content-versions/{content_pk}/1/diff")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
