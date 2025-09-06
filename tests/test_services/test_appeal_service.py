"""Tests for appeal service."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.appeal import AppealCreate
from therobotoverlord_api.database.models.appeal import AppealDecision
from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal import AppealType
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.services.appeal_service import AppealService


class TestAppealService:
    """Test cases for AppealService."""

    @pytest.fixture
    def appeal_service(self):
        """Create appeal service instance for testing."""
        return AppealService()

    @pytest.fixture
    def sample_user_pk(self):
        """Sample user UUID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_appeal_create(self):
        """Sample appeal creation data."""
        return AppealCreate(
            content_type=ContentType.POST,
            content_pk=uuid4(),
            appeal_type=AppealType.SANCTION_APPEAL,
            reason="This post was incorrectly rejected. It follows all community guidelines and provides valuable discussion.",
            evidence="The post contains factual information with proper sources cited.",
        )

    @pytest.fixture
    def sample_appeal_decision(self):
        """Sample appeal decision data."""
        return AppealDecision(
            review_notes="Content violates rule 3.2 regarding inflammatory language.",
        )

    @pytest.mark.asyncio
    async def test_submit_appeal_success(
        self, appeal_service, sample_user_pk, sample_appeal_create
    ):
        """Test successful appeal submission."""
        # Mock the repository methods
        appeal_service.appeal_repository.check_appeal_eligibility = AsyncMock(
            return_value=type(
                "AppealEligibility", (), {"eligible": True, "reason": None}
            )()
        )

        mock_appeal = type(
            "Appeal",
            (),
            {
                "pk": uuid4(),
                "user_pk": sample_user_pk,
                "status": AppealStatus.PENDING,
            },
        )()

        appeal_service.appeal_repository.create_appeal = AsyncMock(
            return_value=mock_appeal
        )
        appeal_service.queue_service.add_appeal_to_queue = AsyncMock()

        # Test appeal submission
        appeal, error = await appeal_service.submit_appeal(
            sample_user_pk, sample_appeal_create
        )

        # Assertions
        assert appeal is not None
        assert error == ""
        assert appeal.pk == mock_appeal.pk
        appeal_service.appeal_repository.create_appeal.assert_called_once()
        appeal_service.queue_service.add_appeal_to_queue.assert_called_once_with(
            mock_appeal.pk
        )

    @pytest.mark.asyncio
    async def test_submit_appeal_not_eligible(
        self, appeal_service, sample_user_pk, sample_appeal_create
    ):
        """Test appeal submission when user is not eligible."""
        # Mock eligibility check to return not eligible
        appeal_service.appeal_repository.check_appeal_eligibility = AsyncMock(
            return_value=type(
                "AppealEligibility",
                (),
                {"eligible": False, "reason": "Daily appeal limit reached"},
            )()
        )

        # Test appeal submission
        appeal, error = await appeal_service.submit_appeal(
            sample_user_pk, sample_appeal_create
        )

        # Assertions
        assert appeal is None
        assert error == "Daily appeal limit reached"

    @pytest.mark.asyncio
    async def test_withdraw_appeal_success(self, appeal_service, sample_user_pk):
        """Test successful appeal withdrawal."""
        appeal_pk = uuid4()

        # Mock appeal with pending status
        mock_appeal = type(
            "Appeal",
            (),
            {
                "pk": appeal_pk,
                "user_pk": sample_user_pk,
                "status": AppealStatus.PENDING,
            },
        )()

        appeal_service.appeal_repository.get = AsyncMock(return_value=mock_appeal)
        appeal_service.appeal_repository.update_appeal = AsyncMock()
        appeal_service.queue_service.remove_appeal_from_queue = AsyncMock()

        # Test withdrawal
        success, error = await appeal_service.withdraw_appeal(appeal_pk, sample_user_pk)

        # Assertions
        assert success is True
        assert error == ""
        appeal_service.appeal_repository.update_appeal.assert_called_once()
        appeal_service.queue_service.remove_appeal_from_queue.assert_called_once_with(
            appeal_pk
        )

    @pytest.mark.asyncio
    async def test_withdraw_appeal_wrong_user(self, appeal_service, sample_user_pk):
        """Test appeal withdrawal by wrong user."""
        appeal_pk = uuid4()
        different_user_pk = uuid4()

        # Mock appeal owned by different user
        mock_appeal = type(
            "Appeal",
            (),
            {
                "pk": appeal_pk,
                "user_pk": different_user_pk,
                "status": AppealStatus.PENDING,
            },
        )()

        appeal_service.appeal_repository.get = AsyncMock(return_value=mock_appeal)

        # Test withdrawal
        success, error = await appeal_service.withdraw_appeal(appeal_pk, sample_user_pk)

        # Assertions
        assert success is False
        assert error == "You can only withdraw your own appeals"

    @pytest.mark.asyncio
    async def test_withdraw_appeal_wrong_status(self, appeal_service, sample_user_pk):
        """Test appeal withdrawal with wrong status."""
        appeal_pk = uuid4()

        # Mock appeal with completed status
        mock_appeal = type(
            "Appeal",
            (),
            {
                "pk": appeal_pk,
                "user_pk": sample_user_pk,
                "status": AppealStatus.SUSTAINED,
            },
        )()

        appeal_service.appeal_repository.get = AsyncMock(return_value=mock_appeal)

        # Test withdrawal
        success, error = await appeal_service.withdraw_appeal(appeal_pk, sample_user_pk)

        # Assertions
        assert success is False
        assert "Cannot withdraw appeal with status: sustained" in error

    @pytest.mark.asyncio
    async def test_assign_appeal_for_review(self, appeal_service):
        """Test assigning appeal for review."""
        appeal_pk = uuid4()
        reviewer_pk = uuid4()

        # Mock pending appeal
        mock_appeal = type(
            "Appeal", (), {"pk": appeal_pk, "status": AppealStatus.PENDING}
        )()

        appeal_service.appeal_repository.get = AsyncMock(return_value=mock_appeal)
        appeal_service.appeal_repository.update_appeal = AsyncMock()

        # Test assignment
        success, error = await appeal_service.assign_appeal_for_review(
            appeal_pk, reviewer_pk
        )

        # Assertions
        assert success is True
        assert error == ""
        appeal_service.appeal_repository.update_appeal.assert_called_once()

    @pytest.mark.asyncio
    async def test_decide_appeal_sustain(self, appeal_service, sample_appeal_decision):
        """Test sustaining an appeal."""
        appeal_pk = uuid4()
        reviewer_pk = uuid4()

        # Mock appeal under review
        mock_appeal = type(
            "Appeal",
            (),
            {
                "pk": appeal_pk,
                "status": AppealStatus.UNDER_REVIEW,
                "reviewed_by": reviewer_pk,
                "user_pk": uuid4(),
            },
        )()

        mock_appeal_repo = AsyncMock()
        mock_loyalty_service = AsyncMock()
        mock_queue_service = AsyncMock()

        appeal_service.appeal_repository.get = AsyncMock(return_value=mock_appeal)
        appeal_service.appeal_repository.update_appeal = mock_appeal_repo.update_appeal
        appeal_service.loyalty_score_service.record_appeal_outcome = (
            mock_loyalty_service.record_appeal_outcome
        )

        # Test decision
        success, error = await appeal_service.decide_appeal(
            appeal_pk, reviewer_pk, AppealStatus.SUSTAINED, sample_appeal_decision
        )

        # Assertions
        assert success is True
        assert error == ""
        mock_appeal_repo.update_appeal.assert_called_once()
        mock_loyalty_service.record_appeal_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_decide_appeal_deny(self, appeal_service, sample_appeal_decision):
        """Test denying an appeal."""
        appeal_pk = uuid4()
        reviewer_pk = uuid4()

        # Mock appeal under review
        mock_appeal = type(
            "Appeal",
            (),
            {
                "pk": appeal_pk,
                "status": AppealStatus.UNDER_REVIEW,
                "reviewed_by": reviewer_pk,
                "user_pk": uuid4(),
            },
        )()

        mock_appeal_repo = AsyncMock()
        mock_loyalty_service = AsyncMock()
        mock_queue_service = AsyncMock()

        appeal_service.appeal_repository.get = AsyncMock(return_value=mock_appeal)
        appeal_service.appeal_repository.update_appeal = mock_appeal_repo.update_appeal
        appeal_service.loyalty_score_service.record_appeal_outcome = (
            mock_loyalty_service.record_appeal_outcome
        )

        # Test decision
        success, error = await appeal_service.decide_appeal(
            appeal_pk, reviewer_pk, AppealStatus.DENIED, sample_appeal_decision
        )

        # Assertions
        assert success is True
        assert error == ""
        appeal_service.appeal_repository.update_appeal.assert_called_once()
        appeal_service.loyalty_score_service.record_appeal_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_decide_appeal_wrong_reviewer(
        self, appeal_service, sample_appeal_decision
    ):
        """Test deciding appeal by wrong reviewer."""
        appeal_pk = uuid4()
        reviewer_pk = uuid4()
        different_reviewer_pk = uuid4()

        # Mock appeal assigned to different reviewer
        mock_appeal = type(
            "Appeal",
            (),
            {
                "pk": appeal_pk,
                "status": AppealStatus.UNDER_REVIEW,
                "reviewed_by": different_reviewer_pk,
            },
        )()

        appeal_service.appeal_repository.get = AsyncMock(return_value=mock_appeal)

        # Test decision
        success, error = await appeal_service.decide_appeal(
            appeal_pk, reviewer_pk, AppealStatus.SUSTAINED, sample_appeal_decision
        )

        # Assertions
        assert success is False
        assert error == "You are not assigned to review this appeal"

    @pytest.mark.asyncio
    async def test_get_user_appeals_paginated(self, appeal_service, sample_user_pk):
        """Test getting user appeals with pagination."""
        # Mock repository response

        mock_appeals = []
        for i in range(3):
            mock_appeal = type(
                "AppealWithContent",
                (),
                {
                    "pk": uuid4(),
                    "user_pk": sample_user_pk,
                    "appellant_username": f"user{i}",
                    "sanction_pk": uuid4(),
                    "flag_pk": None,
                    "appeal_type": AppealType.SANCTION_APPEAL,
                    "appeal_reason": f"Test reason {i}",
                    "status": AppealStatus.PENDING,
                    "reviewed_by": None,
                    "reviewer_username": None,
                    "review_notes": None,
                    "reviewed_at": None,
                    "restoration_completed": False,
                    "restoration_completed_at": None,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                    "sanction_type": "temporary_ban",
                    "sanction_reason": "Violation of community guidelines",
                    "flag_reason": None,
                    "flagged_content_type": None,
                },
            )()
            mock_appeals.append(mock_appeal)

        appeal_service.appeal_repository.get_user_appeals = AsyncMock(
            return_value=mock_appeals
        )
        appeal_service.appeal_repository.count_user_appeals = AsyncMock(return_value=10)

        # Test getting appeals
        response = await appeal_service.get_user_appeals(
            sample_user_pk, page=1, page_size=5
        )

        # Assertions
        assert len(response.appeals) == 3
        assert response.total_count == 10
        assert response.page == 1
        assert response.page_size == 5
        assert response.has_next is True
        assert response.has_previous is False

    @pytest.mark.asyncio
    async def test_get_appeals_queue(self, appeal_service):
        """Test getting appeals queue for moderators."""
        # Mock repository response

        mock_appeals = []
        for i in range(5):
            mock_appeal = type(
                "AppealWithContent",
                (),
                {
                    "pk": uuid4(),
                    "user_pk": uuid4(),
                    "appellant_username": f"user{i}",
                    "sanction_pk": None,
                    "flag_pk": uuid4(),
                    "appeal_type": AppealType.FLAG_APPEAL,
                    "appeal_reason": f"Test reason {i}",
                    "status": AppealStatus.PENDING,
                    "reviewed_by": None,
                    "reviewer_username": None,
                    "review_notes": None,
                    "reviewed_at": None,
                    "restoration_completed": False,
                    "restoration_completed_at": None,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                    "sanction_type": None,
                    "sanction_reason": None,
                    "flag_reason": f"Inappropriate content {i}",
                    "flagged_content_type": "post",
                },
            )()
            mock_appeals.append(mock_appeal)

        appeal_service.appeal_repository.get_appeals_queue = AsyncMock(
            return_value=mock_appeals
        )
        appeal_service.appeal_repository.count = AsyncMock(return_value=15)

        # Test getting queue
        response = await appeal_service.get_appeals_queue(page=1, page_size=10)

        # Assertions
        assert len(response.appeals) == 5
        assert response.total_count == 15
        assert response.has_next is True
        assert response.has_previous is False

    @pytest.mark.asyncio
    async def test_check_appeal_eligibility(self, appeal_service, sample_user_pk):
        """Test checking appeal eligibility."""
        content_pk = uuid4()

        # Mock eligibility response
        mock_eligibility = type(
            "AppealEligibility",
            (),
            {
                "eligible": True,
                "appeals_remaining": 2,
                "max_appeals_per_day": 3,
                "appeals_used_today": 1,
            },
        )()

        appeal_service.appeal_repository.check_appeal_eligibility = AsyncMock(
            return_value=mock_eligibility
        )

        # Test eligibility check
        eligibility = await appeal_service.check_appeal_eligibility(
            sample_user_pk, ContentType.POST, content_pk
        )

        # Assertions
        assert eligibility.eligible is True
        assert eligibility.appeals_remaining == 2
        appeal_service.appeal_repository.check_appeal_eligibility.assert_called_once_with(
            sample_user_pk, ContentType.POST, content_pk
        )

    @pytest.mark.asyncio
    async def test_get_appeal_statistics(self, appeal_service):
        """Test getting appeal statistics."""
        # Mock statistics response
        mock_stats = type(
            "AppealStats",
            (),
            {
                "total_pending": 10,
                "total_under_review": 5,
                "total_sustained": 15,
                "total_denied": 20,
                "total_withdrawn": 3,
                "average_review_time_hours": 24.5,
                "appeals_by_type": {"sanction_appeal": 25, "topic_rejection": 15},
                "top_appellants": [{"username": "user1", "appeal_count": 5}],
                "reviewer_stats": [{"username": "mod1", "reviews_completed": 10}],
            },
        )()

        appeal_service.appeal_repository.get_appeal_statistics = AsyncMock(
            return_value=mock_stats
        )

        # Test getting statistics
        stats = await appeal_service.get_appeal_statistics()

        # Assertions
        assert stats.total_pending == 10
        assert stats.total_sustained == 15
        assert stats.average_review_time_hours == 24.5
        assert len(stats.appeals_by_type) == 2
        assert len(stats.top_appellants) == 1
        assert len(stats.reviewer_stats) == 1
