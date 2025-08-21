"""Edge case and error handling tests for Appeals API."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.appeals import get_appeal_service
from therobotoverlord_api.api.appeals import router as appeals_router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_moderator
from therobotoverlord_api.database.models.appeal import AppealResponse
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User


class TestAppealsAPIEdgeCases:
    """Edge case and error handling tests for Appeals API."""

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

    # Service dependency injection edge cases
    @pytest.mark.asyncio
    async def test_appeal_service_dependency_failure(self, client, test_app, regular_user):
        """Test behavior when appeal service dependency fails."""
        def failing_service():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Service unavailable"
            )

        test_app.dependency_overrides[get_appeal_service] = failing_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "post",
                "content_pk": str(uuid4()),
                "appeal_type": "post_rejection",
                "reason": "Test reason",
                "evidence": "Test evidence",
            },
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Request validation edge cases
    @pytest.mark.asyncio
    async def test_submit_appeal_invalid_json(self, client, test_app, regular_user):
        """Test appeal submission with invalid JSON."""
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.post(
            "/api/v1/appeals/",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_submit_appeal_missing_required_fields(self, client, test_app, regular_user):
        """Test appeal submission with missing required fields."""
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Missing content_pk
        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "post",
                "appeal_type": "post_rejection",
                "reason": "Test reason",
                "evidence": "Test evidence",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing reason
        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "post",
                "content_pk": str(uuid4()),
                "appeal_type": "post_rejection",
                "evidence": "Test evidence",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_appeal_invalid_enum_values(self, client, test_app, regular_user):
        """Test appeal submission with invalid enum values."""
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Invalid content type
        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "invalid_type",
                "content_pk": str(uuid4()),
                "appeal_type": "post_rejection",
                "reason": "Test reason",
                "evidence": "Test evidence",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Invalid appeal type
        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "post",
                "content_pk": str(uuid4()),
                "appeal_type": "invalid_appeal_type",
                "reason": "Test reason",
                "evidence": "Test evidence",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_appeal_extremely_long_text(self, client, test_app, mock_appeal_service, regular_user):
        """Test appeal submission with extremely long text fields."""
        # Create very long strings (assuming there are length limits)
        very_long_reason = "x" * 10000
        very_long_evidence = "y" * 10000

        mock_appeal_service.submit_appeal.return_value = (None, "Text too long")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "post",
                "content_pk": str(uuid4()),
                "appeal_type": "post_rejection",
                "reason": very_long_reason,
                "evidence": very_long_evidence,
            },
        )

        test_app.dependency_overrides.clear()
        # This might be handled at validation level or service level
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # Query parameter edge cases
    @pytest.mark.asyncio
    async def test_eligibility_check_missing_parameters(self, client, test_app, regular_user):
        """Test eligibility check with missing query parameters."""
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Missing content_pk
        response = client.get("/api/v1/appeals/eligibility?content_type=post")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing content_type
        response = client.get(f"/api/v1/appeals/eligibility?content_pk={uuid4()}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_pagination_boundary_values(self, client, test_app, mock_appeal_service, regular_user):
        """Test pagination with boundary values."""
        mock_response = AppealResponse(
            appeals=[],
            total_count=0,
            page=1,
            page_size=1,
            has_next=False,
            has_previous=False,
        )
        mock_appeal_service.get_user_appeals.return_value = mock_response

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Test minimum valid values
        response = client.get("/api/v1/appeals/my-appeals?page=1&page_size=1")
        assert response.status_code == status.HTTP_200_OK

        # Test maximum valid page size
        response = client.get("/api/v1/appeals/my-appeals?page=1&page_size=100")
        assert response.status_code == status.HTTP_200_OK

        test_app.dependency_overrides.clear()

    # Service exception handling
    @pytest.mark.asyncio
    async def test_service_exceptions_during_appeal_operations(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test handling of service exceptions during various operations."""
        appeal_pk = uuid4()

        # Test exception during appeal retrieval - mock service method to raise HTTPException
        mock_appeal_service.get_appeal_by_id.side_effect = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get(f"/api/v1/appeals/my-appeals/{appeal_pk}")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_concurrent_appeal_operations(self, client, test_app, mock_appeal_service, regular_user):
        """Test handling of concurrent operations on the same appeal."""
        appeal_pk = uuid4()

        # Simulate concurrent modification error
        mock_appeal_service.withdraw_appeal.return_value = (
            False,
            "Appeal was modified by another process",
        )

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.patch(f"/api/v1/appeals/my-appeals/{appeal_pk}/withdraw")

        test_app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "modified by another process" in response.json()["detail"]

    # Content type and UUID validation edge cases
    @pytest.mark.asyncio
    async def test_malformed_uuid_handling(self, client, test_app, mock_appeal_service, regular_user):
        """Test handling of malformed UUIDs in various endpoints."""
        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        malformed_uuids = [
            "not-a-uuid",
            "12345",
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        ]

        for malformed_uuid in malformed_uuids:
            # Test appeal retrieval with malformed UUID
            response = client.get(f"/api/v1/appeals/my-appeals/{malformed_uuid}")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test content retrieval with malformed UUID
            response = client.get(f"/api/v1/appeals/content/post/{malformed_uuid}")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_content_type_case_sensitivity(self, client, test_app, mock_appeal_service, regular_user):
        """Test content type parameter case sensitivity."""
        content_pk = uuid4()
        mock_appeal_service.get_appealable_content.return_value = {"test": "data"}

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Test different cases - these should all be invalid
        invalid_cases = ["POST", "Post", "pOsT", "TOPIC", "Topic"]

        for case in invalid_cases:
            response = client.get(f"/api/v1/appeals/content/{case}/{content_pk}")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()

    # Moderator-specific edge cases
    @pytest.mark.asyncio
    async def test_moderator_decision_with_empty_data(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test moderator decisions with empty or minimal data."""
        appeal_pk = uuid4()
        mock_appeal_service.decide_appeal.return_value = (True, "")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        # Test with empty strings
        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/sustain",
            json={"decision_reason": "", "review_notes": ""},
        )
        # This might be valid or invalid depending on business rules
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

        # Test with only whitespace
        response = client.patch(
            f"/api/v1/appeals/queue/{appeal_pk}/deny",
            json={"decision_reason": "   ", "review_notes": "\t\n"},
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_queue_with_extreme_pagination(
        self, client, test_app, mock_appeal_service, moderator_user
    ):
        """Test appeals queue with extreme pagination values."""
        mock_response = AppealResponse(
            appeals=[],
            total_count=0,
            page=1,
            page_size=1,
            has_next=False,
            has_previous=False,
        )
        mock_appeal_service.get_appeals_queue.return_value = mock_response

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: moderator_user
        test_app.dependency_overrides[require_moderator] = lambda: moderator_user

        # Test very high page number (should be handled gracefully)
        response = client.get("/api/v1/appeals/queue?page=999999")
        assert response.status_code == status.HTTP_200_OK

        test_app.dependency_overrides.clear()

    # Network and timeout simulation
    @pytest.mark.asyncio
    async def test_service_timeout_simulation(self, client, test_app, regular_user):
        """Test behavior when service operations timeout."""
        def timeout_service():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Operation timed out"
            )

        test_app.dependency_overrides[get_appeal_service] = timeout_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        response = client.get("/api/v1/appeals/my-appeals")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        test_app.dependency_overrides.clear()

    # Content encoding edge cases
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(
        self, client, test_app, mock_appeal_service, regular_user
    ):
        """Test handling of Unicode and special characters in appeal data."""
        mock_appeal_service.submit_appeal.return_value = (None, "Invalid characters")

        test_app.dependency_overrides[get_appeal_service] = lambda: mock_appeal_service
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Test with various Unicode characters
        unicode_test_cases = [
            "Test with émojis 🚀🎉",
            "Chinese characters: 你好世界",
            "Arabic text: مرحبا بالعالم",
            "Special chars: @#$%^&*()_+-=[]{}|;':\",./<>?",
            "Zero-width characters: \u200b\u200c\u200d",
        ]

        for test_case in unicode_test_cases:
            response = client.post(
                "/api/v1/appeals/",
                json={
                    "content_type": "post",
                    "content_pk": str(uuid4()),
                    "appeal_type": "post_rejection",
                    "reason": test_case,
                    "evidence": f"Evidence: {test_case}",
                },
            )
            # Should handle Unicode gracefully
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_201_CREATED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_null_and_undefined_values(self, client, test_app, regular_user):
        """Test handling of null and undefined values in requests."""
        test_app.dependency_overrides[get_current_user] = lambda: regular_user

        # Test with explicit null values
        response = client.post(
            "/api/v1/appeals/",
            json={
                "content_type": "post",
                "content_pk": str(uuid4()),
                "appeal_type": "post_rejection",
                "reason": None,  # Explicit null
                "evidence": "Test evidence",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        test_app.dependency_overrides.clear()
