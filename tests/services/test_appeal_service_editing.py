"""Tests for AppealService content editing functionality."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.appeal import Appeal
from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal import AppealType
from therobotoverlord_api.database.models.appeal_with_editing import (
    AppealDecisionWithEdit,
)
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.content_version import RestorationResult
from therobotoverlord_api.services.appeal_service import AppealService


class TestAppealServiceEditing:
    """Test cases for AppealService content editing functionality."""

    @pytest.fixture
    def mock_appeal_repo(self):
        """Mock appeal repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_loyalty_service(self):
        """Mock loyalty score service."""
        return AsyncMock()

    @pytest.fixture
    def mock_restoration_service(self):
        """Mock content restoration service."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_appeal_repo, mock_loyalty_service, mock_restoration_service):
        """AppealService instance with mocked dependencies."""
        service = AppealService()
        service.appeal_repository = mock_appeal_repo
        service.loyalty_score_service = mock_loyalty_service
        service.content_restoration_service = mock_restoration_service
        return service

    @pytest.fixture
    def sample_appeal(self):
        """Sample appeal for testing."""
        reviewer_pk = uuid4()
        appeal = Appeal(
            pk=uuid4(),
            user_pk=uuid4(),
            sanction_pk=None,
            flag_pk=uuid4(),
            appeal_type=AppealType.FLAG_APPEAL,
            status=AppealStatus.UNDER_REVIEW,
            appeal_reason="Content was incorrectly flagged",
            reviewed_by=reviewer_pk,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        # Store reviewer_pk as an attribute for tests to use
        appeal._test_reviewer_pk = reviewer_pk  # type: ignore[attr-defined]
        return appeal

    @pytest.mark.asyncio
    async def test_decide_appeal_with_edit_sustained_no_edits(
        self,
        service,
        sample_appeal,
        mock_appeal_repo,
        mock_loyalty_service,
        mock_restoration_service,
    ):
        """Test sustaining appeal without content edits."""
        reviewer_pk = sample_appeal._test_reviewer_pk
        decision_data = AppealDecisionWithEdit(
            review_notes="Content was incorrectly flagged",
            edit_content=False,
            edited_title=None,
            edited_content=None,
            edited_description=None,
            edit_reason=None,
        )

        mock_appeal_repo.get.return_value = sample_appeal
        mock_restoration_result = RestorationResult(
            success=True,
            content_type=ContentType.POST,
            content_pk=sample_appeal.flag_pk,  # Use flag_pk since this is a FLAG_APPEAL appeal
            version_pk=uuid4(),
            restoration_pk=uuid4(),
            content_edited=False,
        )
        mock_restoration_service.restore_with_edits.return_value = (
            mock_restoration_result
        )

        success, error = await service.decide_appeal_with_edit(
            appeal_pk=sample_appeal.pk,
            reviewer_pk=reviewer_pk,
            decision=AppealStatus.SUSTAINED,
            decision_data=decision_data,
            edited_content=None,
        )

        assert success is True
        assert error == ""

        mock_appeal_repo.get.assert_called_once_with(sample_appeal.pk)
        mock_appeal_repo.update_appeal.assert_called_once()
        mock_restoration_service.restore_with_edits.assert_called_once_with(
            content_type=ContentType.POST,
            content_pk=sample_appeal.flag_pk,
            appeal=sample_appeal,
            reviewer_pk=reviewer_pk,
            edited_content=None,
            edit_reason=None,
        )
        mock_loyalty_service.record_appeal_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_decide_appeal_with_edit_sustained_with_edits(
        self,
        service,
        sample_appeal,
        mock_appeal_repo,
        mock_loyalty_service,
        mock_restoration_service,
    ):
        """Test sustaining appeal with content edits."""
        reviewer_pk = sample_appeal._test_reviewer_pk
        edited_content = {"title": "Edited Title", "body": "Edited content"}
        decision_data = AppealDecisionWithEdit(
            review_notes="Fixed inappropriate language",
            edit_content=True,
            edited_title="Edited Title",
            edited_content="Edited content",
            edited_description="Edited description",
            edit_reason="Removed offensive terms",
        )

        mock_appeal_repo.get.return_value = sample_appeal
        mock_restoration_result = RestorationResult(
            success=True,
            content_type=ContentType.POST,
            content_pk=sample_appeal.flag_pk,
            version_pk=uuid4(),
            restoration_pk=uuid4(),
            content_edited=True,
        )
        mock_restoration_service.restore_with_edits.return_value = (
            mock_restoration_result
        )

        success, error = await service.decide_appeal_with_edit(
            appeal_pk=sample_appeal.pk,
            reviewer_pk=reviewer_pk,
            decision=AppealStatus.SUSTAINED,
            decision_data=decision_data,
            edited_content=edited_content,
        )

        assert success is True
        assert error == ""

        mock_restoration_service.restore_with_edits.assert_called_once_with(
            content_type=ContentType.POST,
            content_pk=sample_appeal.flag_pk,
            appeal=sample_appeal,
            reviewer_pk=reviewer_pk,
            edited_content=edited_content,
            edit_reason=decision_data.edit_reason,
        )

    @pytest.mark.asyncio
    async def test_decide_appeal_with_edit_denied(
        self, service, sample_appeal, mock_appeal_repo, mock_loyalty_service
    ):
        """Test denying appeal with detailed reasoning."""
        reviewer_pk = sample_appeal._test_reviewer_pk
        decision_data = AppealDecisionWithEdit(
            review_notes="Content violates community guidelines",
            edit_content=False,
            edited_title=None,
            edited_content=None,
            edited_description=None,
            edit_reason=None,
        )

        mock_appeal_repo.get.return_value = sample_appeal

        success, error = await service.decide_appeal_with_edit(
            appeal_pk=sample_appeal.pk,
            reviewer_pk=reviewer_pk,
            decision=AppealStatus.DENIED,
            decision_data=decision_data,
        )

        assert success is True
        assert error == ""

        mock_appeal_repo.get.assert_called_once_with(sample_appeal.pk)
        mock_appeal_repo.update_appeal.assert_called_once()
        mock_loyalty_service.record_appeal_outcome.assert_called_once_with(
            user_pk=sample_appeal.user_pk,
            appeal_pk=sample_appeal.pk,
            outcome="denied",
            points_awarded=-5,
        )

    @pytest.mark.asyncio
    async def test_decide_appeal_with_edit_invalid_decision(
        self, service, sample_appeal
    ):
        """Test invalid decision status."""
        reviewer_pk = uuid4()
        decision_data = AppealDecisionWithEdit(
            review_notes="Test",
            edit_content=False,
            edited_title=None,
            edited_content=None,
            edited_description=None,
            edit_reason=None,
        )

        success, error = await service.decide_appeal_with_edit(
            appeal_pk=sample_appeal.pk,
            reviewer_pk=reviewer_pk,
            decision=AppealStatus.PENDING,  # Invalid decision
            decision_data=decision_data,
        )

        assert success is False
        assert error == "Decision must be either SUSTAINED or DENIED"

    @pytest.mark.asyncio
    async def test_decide_appeal_with_edit_appeal_not_found(
        self, service, mock_appeal_repo
    ):
        """Test appeal not found."""
        appeal_pk = uuid4()
        reviewer_pk = uuid4()
        decision_data = AppealDecisionWithEdit(
            review_notes="Test",
            edit_content=False,
            edited_title=None,
            edited_content=None,
            edited_description=None,
            edit_reason=None,
        )

        mock_appeal_repo.get.return_value = None

        success, error = await service.decide_appeal_with_edit(
            appeal_pk=appeal_pk,
            reviewer_pk=reviewer_pk,
            decision=AppealStatus.SUSTAINED,
            decision_data=decision_data,
        )

        assert success is False
        assert error == "Appeal not found"

    @pytest.mark.asyncio
    async def test_decide_appeal_with_edit_wrong_reviewer(
        self, service, sample_appeal, mock_appeal_repo
    ):
        """Test wrong reviewer assigned."""
        wrong_reviewer_pk = uuid4()
        decision_data = AppealDecisionWithEdit(
            review_notes="Test",
            edit_content=False,
            edited_title=None,
            edited_content=None,
            edited_description=None,
            edit_reason=None,
        )

        mock_appeal_repo.get.return_value = sample_appeal

        success, error = await service.decide_appeal_with_edit(
            appeal_pk=sample_appeal.pk,
            reviewer_pk=wrong_reviewer_pk,
            decision=AppealStatus.SUSTAINED,
            decision_data=decision_data,
        )

        assert success is False
        assert error == "You are not assigned to review this appeal"

    @pytest.mark.asyncio
    async def test_decide_appeal_with_edit_wrong_status(
        self, service, mock_appeal_repo
    ):
        """Test appeal not under review."""
        appeal = Appeal(
            pk=uuid4(),
            user_pk=uuid4(),
            flag_pk=uuid4(),
            appeal_type=AppealType.FLAG_APPEAL,
            appeal_reason="This is a test appeal reason",
            status=AppealStatus.SUSTAINED,  # Already decided
            reviewed_by=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        decision_data = AppealDecisionWithEdit(
            review_notes="Test",
            edit_content=False,
            edited_title=None,
            edited_content=None,
            edited_description=None,
            edit_reason=None,
        )

        mock_appeal_repo.get.return_value = appeal

        success, error = await service.decide_appeal_with_edit(
            appeal_pk=appeal.pk,
            reviewer_pk=appeal.reviewed_by,
            decision=AppealStatus.SUSTAINED,
            decision_data=decision_data,
        )

        assert success is False
        assert error == f"Appeal is not under review (status: {appeal.status})"
