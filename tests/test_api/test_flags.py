"""Integration tests for Flag API endpoints."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient

from therobotoverlord_api.api.flags import router as flags_router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.flag import Flag
from therobotoverlord_api.database.models.flag import FlagStatus
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.flag_service import FlagService
from therobotoverlord_api.services.flag_service import get_flag_service


# Create test app without authentication middleware
def create_test_app():
    """Create FastAPI test app without authentication middleware."""
    test_app = FastAPI(title="Test API")
    test_app.include_router(flags_router, prefix="/api/v1")
    return test_app


@pytest.fixture
def test_app():
    """Test app fixture without authentication middleware."""
    return create_test_app()


@pytest.fixture
def test_client(test_app):
    """Test client fixture using test app without auth middleware."""
    return TestClient(test_app)


@pytest.fixture
def sample_post_for_flagging():
    """Sample post data for flagging tests."""
    return {
        "pk": str(uuid4()),
        "topic_pk": str(uuid4()),
        "content": "This is a test post that will be flagged",
        "author_pk": str(uuid4()),
        "status": ContentStatus.APPROVED.value,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": None,
    }


@pytest.fixture
def sample_topic_for_flagging():
    """Sample topic data for flagging tests."""
    return {
        "pk": str(uuid4()),
        "title": "Test Topic for Flagging",
        "description": "A topic to test flagging functionality",
        "author_pk": str(uuid4()),
        "status": TopicStatus.APPROVED.value,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": None,
    }


@pytest.fixture
def mock_current_user():
    """Mock current user for testing."""
    return User(
        pk=uuid4(),
        created_at=datetime.now(UTC),
        google_id="test_google_id",
        username="testuser",
        email="testuser@example.com",
        role=UserRole.MODERATOR,
        loyalty_score=500,
        is_banned=False,
        is_sanctioned=False,
        email_verified=False,
    )


@pytest.fixture
def mock_moderator_user():
    """Mock moderator user for API tests."""
    return User(
        pk=uuid4(),
        username="moderator",
        email="moderator@example.com",
        role=UserRole.MODERATOR,
        loyalty_score=500,
        is_banned=False,
        google_id="987654321",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_flag_service_for_api():
    """Mock flag service for API tests."""
    service = AsyncMock(spec=FlagService)

    # Mock create_flag with side_effect to handle validation
    def mock_create_flag(flag_data, user_pk):
        # Check for validation errors that should raise ValueError
        post_pk = getattr(flag_data, "post_pk", None)
        topic_pk = getattr(flag_data, "topic_pk", None)

        if not post_pk and not topic_pk:
            raise ValueError("Must specify either post_pk or topic_pk")
        if post_pk and topic_pk:
            raise ValueError("Cannot flag both post and topic")
        # Allow sample post UUIDs - check if it's a valid UUID format
        if post_pk:
            try:
                # If it's a valid UUID, allow it (except for specific test cases)
                from uuid import UUID

                UUID(str(post_pk))
                # Only reject specific test UUIDs that should simulate nonexistent posts
                # This allows the sample_post_for_flagging fixture to work with any UUID
                if str(flag_data.post_pk) in ["00000000-0000-0000-0000-000000000000"]:
                    raise ValueError("Post not found")
            except ValueError as e:
                if "Post not found" in str(e):
                    raise
                # Invalid UUID format
                raise ValueError("Post not found") from None

        # Return appropriate Flag object based on input
        if hasattr(flag_data, "topic_pk") and flag_data.topic_pk:
            return Flag(
                pk=uuid4(),
                post_pk=None,
                topic_pk=flag_data.topic_pk,
                flagger_pk=user_pk,
                reason=flag_data.reason,
                status=FlagStatus.PENDING,
                reviewed_by_pk=None,
                reviewed_at=None,
                review_notes=None,
                created_at=datetime.now(UTC),
                updated_at=None,
            )
        return Flag(
            pk=uuid4(),
            post_pk=flag_data.post_pk,
            topic_pk=None,
            flagger_pk=user_pk,
            reason=flag_data.reason,
            status=FlagStatus.PENDING,
            reviewed_by_pk=None,
            reviewed_at=None,
            review_notes=None,
            created_at=datetime.now(UTC),
            updated_at=None,
        )

    service.create_flag.side_effect = mock_create_flag

    # Mock flag_repo attribute
    mock_flag_repo = AsyncMock()
    # Create a sample flag for repo methods
    sample_flag = Flag(
        pk=uuid4(),
        post_pk=uuid4(),
        topic_pk=None,
        flagger_pk=uuid4(),
        reason="Sample flag",
        status=FlagStatus.PENDING,
        reviewed_by_pk=None,
        reviewed_at=None,
        review_notes=None,
        created_at=datetime.now(UTC),
        updated_at=None,
    )
    mock_flag_repo.get_flags_for_review.return_value = [sample_flag]

    # Create a known flag for get_by_pk tests
    known_flag_pk = uuid4()
    known_flag = Flag(
        pk=known_flag_pk,
        post_pk=uuid4(),
        topic_pk=None,
        flagger_pk=uuid4(),
        reason="Known test flag",
        status=FlagStatus.PENDING,
        reviewed_by_pk=None,
        reviewed_at=None,
        review_notes=None,
        created_at=datetime.now(UTC),
        updated_at=None,
    )

    # Mock get_by_pk to return the known flag for its UUID
    def mock_get_by_pk(pk):
        if str(pk) == str(known_flag_pk):
            return known_flag
        return None

    mock_flag_repo.get_by_pk.side_effect = mock_get_by_pk
    mock_flag_repo.get_user_flags.return_value = [sample_flag]
    mock_flag_repo.get_content_flags.return_value = [sample_flag]

    # Store the known flag for tests to use
    service._test_known_flag = known_flag
    service.flag_repo = mock_flag_repo

    # Mock service methods
    service.get_user_flag_stats.return_value = {
        "total_flags": 1,
        "pending": 1,
        "upheld": 0,
        "dismissed": 0,
    }

    service.get_content_flag_summary.return_value = {
        "total_flags": 1,
        "pending": 1,
        "upheld": 0,
        "dismissed": 0,
    }

    return service


class TestFlagCreation:
    """Test flag creation endpoints."""

    @pytest.mark.asyncio
    async def test_create_flag_for_post_success(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test successfully creating a flag for a post."""

        # Create a mock function that returns the user directly
        async def mock_get_current_user():
            return mock_current_user

        def mock_get_flag_service():
            return mock_flag_service_for_api

        # Override dependencies
        test_app.dependency_overrides[get_current_user] = mock_get_current_user
        test_app.dependency_overrides[get_flag_service] = mock_get_flag_service

        try:
            flag_data = {
                "post_pk": sample_post_for_flagging["pk"],
                "reason": "This post contains inappropriate content that violates community guidelines",
            }

            response = test_client.post(
                "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
            )

            assert response.status_code == status.HTTP_201_CREATED
            response_data = response.json()
            assert "pk" in response_data

            # Verify the mock was called correctly
            mock_flag_service_for_api.create_flag.assert_called_once()

        finally:
            # Clean up dependency overrides
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_flag_for_topic_success(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        sample_topic_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test successful flag creation for a topic."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        flag_data = {
            "topic_pk": sample_topic_for_flagging["pk"],
            "reason": "This topic contains inappropriate content",
        }

        response = test_client.post(
            "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["post_pk"] is None
        assert response_data["topic_pk"] == sample_topic_for_flagging["pk"]
        assert response_data["reason"] == flag_data["reason"]
        assert response_data["status"] == FlagStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_create_flag_unauthenticated(self, test_client):
        """Test that unauthenticated users cannot create flags."""
        # No dependency overrides - should fail authentication
        flag_data = {
            "post_pk": "550e8400-e29b-41d4-a716-446655440000",
            "reason": "Test flag",
        }

        response = test_client.post("/api/v1/flags/", json=flag_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_flag_invalid_reason_too_short(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test flag creation with reason too short."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        flag_data = {
            "post_pk": sample_post_for_flagging["pk"],
            "reason": "short",  # Less than 10 characters
        }

        response = test_client.post(
            "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_flag_invalid_reason_too_long(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test flag creation with reason too long."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        flag_data = {
            "post_pk": sample_post_for_flagging["pk"],
            "reason": "x" * 501,  # More than 500 characters
        }

        response = test_client.post(
            "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_flag_no_content_specified(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test flag creation without specifying content."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        flag_data = {"reason": "This flag has no content specified"}

        response = test_client.post(
            "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Must specify either post_pk or topic_pk" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_flag_both_content_specified(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test flag creation with both post and topic specified."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        flag_data = {
            "post_pk": str(uuid4()),
            "topic_pk": str(uuid4()),
            "reason": "This flag specifies both content types",
        }

        response = test_client.post(
            "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot flag both post and topic" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_flag_nonexistent_post(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test flag creation for nonexistent post."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        flag_data = {
            "post_pk": "00000000-0000-0000-0000-000000000000",
            "reason": "This post does not exist",
        }

        response = test_client.post(
            "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Post not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_flag_duplicate_prevention(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test prevention of duplicate flags from same user."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        # Configure mock service to handle duplicate prevention
        call_count = 0

        def mock_create_with_duplicate_check(flag_data, user_pk):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call succeeds
                return Flag(
                    pk=uuid4(),
                    post_pk=flag_data.post_pk,
                    topic_pk=None,
                    flagger_pk=user_pk,
                    reason=flag_data.reason,
                    status=FlagStatus.PENDING,
                    reviewed_by_pk=None,
                    reviewed_at=None,
                    review_notes=None,
                    created_at=datetime.now(UTC),
                    updated_at=None,
                )
            # Second call fails with duplicate error
            raise ValueError("User has already flagged this content")

        mock_flag_service_for_api.create_flag.side_effect = (
            mock_create_with_duplicate_check
        )

        flag_data = {
            "post_pk": sample_post_for_flagging["pk"],
            "reason": "First flag for this content",
        }

        # Create first flag
        response1 = test_client.post(
            "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create duplicate flag
        flag_data["reason"] = "Duplicate flag attempt"
        response2 = test_client.post(
            "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
        )

        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already flagged this content" in response2.json()["detail"]


class TestFlagRetrieval:
    """Test flag retrieval endpoints."""

    @pytest.mark.asyncio
    async def test_get_flags_as_moderator(
        self,
        test_client,
        test_app,
        async_client: AsyncClient,
        moderator_user_headers,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test getting flags as a moderator."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            # Create a flag first
            flag_data = {
                "post_pk": sample_post_for_flagging["pk"],
                "reason": "Test flag for moderator review",
            }

            await async_client.post(
                "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
            )

            # Get flags as moderator
            response = test_client.get("/api/v1/flags/", headers=moderator_user_headers)
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        flags = response.json()
        assert isinstance(flags, list)
        assert len(flags) >= 1

        # Check flag structure
        flag = flags[0]
        assert "pk" in flag
        assert "post_pk" in flag
        assert "flagger_pk" in flag
        assert "reason" in flag
        assert "status" in flag
        assert "created_at" in flag

    @pytest.mark.asyncio
    async def test_get_flags_as_citizen_forbidden(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        mock_current_user,
        mock_flag_service_for_api,
    ):
        """Test that citizens cannot list all flags."""
        # Create a citizen user (not moderator)
        citizen_user = User(
            pk=uuid4(),
            username="citizen_user",
            email="citizen@test.com",
            google_id="google_citizen_123",
            role=UserRole.CITIZEN,
            loyalty_score=100,
            is_banned=False,
            is_sanctioned=False,
            email_verified=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: citizen_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            response = test_client.get("/api/v1/flags/", headers=citizen_user_headers)
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_flags_unauthenticated(self, test_client):
        """Test that unauthenticated users cannot list flags."""
        # No dependency overrides - should fail authentication
        response = test_client.get("/api/v1/flags/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_flags_with_pagination(
        self,
        test_client,
        test_app,
        moderator_user_headers,
        mock_current_user,
        mock_flag_service_for_api,
    ):
        """Test flag listing with pagination."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            response = test_client.get(
                "/api/v1/flags/?limit=10&offset=0", headers=moderator_user_headers
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        flags = response.json()
        assert isinstance(flags, list)
        assert len(flags) <= 10

    @pytest.mark.asyncio
    async def test_get_flags_with_status_filter(
        self,
        test_client,
        test_app,
        moderator_user_headers,
        mock_current_user,
        mock_flag_service_for_api,
    ):
        """Test flag listing with status filter."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            response = test_client.get(
                "/api/v1/flags/?status_filter=pending", headers=moderator_user_headers
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        flags = response.json()
        assert isinstance(flags, list)

        # All returned flags should be pending
        for flag in flags:
            assert flag["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_flag_by_id_as_flagger(
        self,
        test_client,
        test_app,
        async_client: AsyncClient,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test getting specific flag as the flagger."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            # Create flag
            flag_data = {
                "post_pk": sample_post_for_flagging["pk"],
                "reason": "Test flag for individual retrieval",
            }

            create_response = await async_client.post(
                "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
            )

            # Get flag by ID (use the known test flag)
            known_flag_pk = mock_flag_service_for_api._test_known_flag.pk
            response = test_client.get(
                f"/api/v1/flags/{known_flag_pk}", headers=citizen_user_headers
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        retrieved_flag = response.json()
        assert retrieved_flag["pk"] == str(known_flag_pk)
        assert (
            retrieved_flag["reason"]
            == mock_flag_service_for_api._test_known_flag.reason
        )

    @pytest.mark.asyncio
    async def test_get_flag_by_id_as_moderator(
        self,
        test_client,
        test_app,
        async_client: AsyncClient,
        moderator_user_headers,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test getting specific flag as a moderator."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            # Create flag as citizen
            flag_data = {
                "post_pk": sample_post_for_flagging["pk"],
                "reason": "Test flag for moderator access",
            }

            create_response = await async_client.post(
                "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
            )

            # Get flag as moderator (use the known test flag)
            known_flag_pk = mock_flag_service_for_api._test_known_flag.pk
            response = test_client.get(
                f"/api/v1/flags/{known_flag_pk}", headers=moderator_user_headers
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_flag_by_id_unauthorized(
        self,
        test_client,
        test_app,
        async_client: AsyncClient,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test getting flag by different user (unauthorized)."""
        # Override dependencies for flag creation
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            # Create flag with one user
            flag_data = {
                "post_pk": sample_post_for_flagging["pk"],
                "reason": "Test flag for unauthorized access",
            }

            create_response = await async_client.post(
                "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
            )

            # Get the mock flag pk for later use
            mock_flag_pk = mock_flag_service_for_api.create_flag.return_value.pk
        finally:
            test_app.dependency_overrides.clear()

        # Try to access with unauthenticated request (no dependency overrides)
        response = test_client.get(f"/api/v1/flags/{mock_flag_pk}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_nonexistent_flag(
        self,
        test_client,
        test_app,
        moderator_user_headers,
        mock_current_user,
        mock_flag_service_for_api,
    ):
        """Test getting a flag that doesn't exist."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            nonexistent_id = str(uuid4())

            response = test_client.get(
                f"/api/v1/flags/{nonexistent_id}", headers=moderator_user_headers
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestFlagStatistics:
    """Test flag statistics endpoints."""

    @pytest.mark.asyncio
    async def test_get_user_flag_stats_own(
        self,
        test_client,
        test_app,
        async_client: AsyncClient,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test getting own flag statistics."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            # Create some flags
            flag_data = {
                "post_pk": sample_post_for_flagging["pk"],
                "reason": "Test flag for statistics",
            }

            await async_client.post(
                "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
            )

            # Get flag stats (use mock user's pk directly)
            response = test_client.get(
                f"/api/v1/flags/stats/user/{mock_current_user.pk}",
                headers=citizen_user_headers,
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        stats = response.json()

        assert "total_flags" in stats
        assert "pending" in stats
        assert "upheld" in stats
        assert "dismissed" in stats
        assert stats["total_flags"] >= 1

    @pytest.mark.asyncio
    async def test_get_user_flag_stats_as_moderator(
        self,
        test_client,
        test_app,
        async_client: AsyncClient,
        moderator_user_headers,
        citizen_user_headers,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test getting user flag statistics as a moderator."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            # Get stats as moderator (use mock user's pk directly)
            response = test_client.get(
                f"/api/v1/flags/stats/user/{mock_current_user.pk}",
                headers=moderator_user_headers,
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_content_flag_stats_as_moderator(
        self,
        test_client,
        test_app,
        async_client: AsyncClient,
        moderator_user_headers,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
        mock_current_user,
    ):
        """Test getting content flag statistics as a moderator."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            # Create flag for the post
            flag_data = {
                "post_pk": sample_post_for_flagging["pk"],
                "reason": "Test flag for content statistics",
            }

            await async_client.post(
                "/api/v1/flags/", json=flag_data, headers=citizen_user_headers
            )

            # Get content stats
            response = test_client.get(
                f"/api/v1/flags/stats/content/post/{sample_post_for_flagging['pk']}",
                headers=moderator_user_headers,
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        stats = response.json()

        assert "total_flags" in stats
        assert "pending" in stats
        assert "upheld" in stats
        assert "dismissed" in stats
        assert stats["total_flags"] >= 1

    @pytest.mark.asyncio
    async def test_get_content_flag_stats_as_citizen_forbidden(
        self,
        test_client,
        test_app,
        citizen_user_headers,
        sample_post_for_flagging,
        mock_flag_service_for_api,
    ):
        """Test that citizens cannot get content flag statistics."""
        # Create a citizen user for this test
        citizen_user = User(
            pk=uuid4(),
            email="citizen@test.com",
            google_id="citizen123",
            username="citizen",
            role=UserRole.CITIZEN,
            loyalty_score=100,
            is_banned=False,
            is_sanctioned=False,
            email_verified=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: citizen_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            response = test_client.get(
                f"/api/v1/flags/stats/content/post/{sample_post_for_flagging['pk']}",
                headers=citizen_user_headers,
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_content_flag_stats_invalid_type(
        self,
        test_client,
        test_app,
        moderator_user_headers,
        mock_current_user,
        mock_flag_service_for_api,
    ):
        """Test getting content flag stats with invalid content type."""
        # Override dependencies
        test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
        test_app.dependency_overrides[get_flag_service] = (
            lambda: mock_flag_service_for_api
        )

        try:
            content_id = str(uuid4())

            response = test_client.get(
                f"/api/v1/flags/stats/content/invalid/{content_id}",
                headers=moderator_user_headers,
            )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Content type must be 'post' or 'topic'" in response.json()["detail"]
