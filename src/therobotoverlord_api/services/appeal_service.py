"""Appeal service for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from uuid import UUID

from therobotoverlord_api.database.models.appeal import Appeal
from therobotoverlord_api.database.models.appeal import AppealCreate
from therobotoverlord_api.database.models.appeal import AppealDecision
from therobotoverlord_api.database.models.appeal import AppealEligibility
from therobotoverlord_api.database.models.appeal import AppealResponse
from therobotoverlord_api.database.models.appeal import AppealStats
from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal import AppealUpdate
from therobotoverlord_api.database.models.appeal import AppealWithContent
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.repositories.appeal import AppealRepository
from therobotoverlord_api.services.loyalty_score_service import LoyaltyScoreService
from therobotoverlord_api.services.queue_service import QueueService


class AppealService:
    """Service for managing appeals workflow."""

    def __init__(
        self,
        appeal_repository: AppealRepository | None = None,
        loyalty_score_service: LoyaltyScoreService | None = None,
        queue_service: QueueService | None = None,
    ):
        self.appeal_repository = appeal_repository or AppealRepository()
        self.loyalty_score_service = loyalty_score_service or LoyaltyScoreService()
        self.queue_service = queue_service or QueueService()

    async def submit_appeal(
        self, user_pk: UUID, appeal_data: AppealCreate
    ) -> tuple[Appeal | None, str]:
        """
        Submit a new appeal.

        Returns:
            Tuple of (Appeal, error_message). Appeal is None if submission failed.
        """
        # Check eligibility first
        eligibility = await self.check_appeal_eligibility(
            user_pk, appeal_data.content_type, appeal_data.content_pk
        )

        if not eligibility.eligible:
            return None, eligibility.reason or "Appeal not eligible"

        # Create the appeal
        appeal = await self.appeal_repository.create_appeal(appeal_data, user_pk)

        # Add to appeals queue for processing
        await self.queue_service.add_appeal_to_queue(appeal.pk)

        return appeal, ""

    async def check_appeal_eligibility(
        self, user_pk: UUID, content_type: ContentType, content_pk: UUID
    ) -> AppealEligibility:
        """Check if user can appeal specific content."""
        return await self.appeal_repository.check_appeal_eligibility(
            user_pk, content_type, content_pk
        )

    async def get_user_appeals(
        self,
        user_pk: UUID,
        status: AppealStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AppealResponse:
        """Get paginated appeals for a user."""
        offset = (page - 1) * page_size

        appeals = await self.appeal_repository.get_user_appeals(
            user_pk, status, page_size, offset
        )

        total_count = await self.appeal_repository.count_user_appeals(user_pk, status)

        return AppealResponse(
            appeals=appeals,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total_count,
            has_previous=page > 1,
        )

    async def withdraw_appeal(self, appeal_pk: UUID, user_pk: UUID) -> tuple[bool, str]:
        """
        Withdraw an appeal (user can only withdraw their own pending appeals).

        Returns:
            Tuple of (success, error_message)
        """
        # Get the appeal
        appeal = await self.appeal_repository.get(appeal_pk)
        if not appeal:
            return False, "Appeal not found"

        # Verify ownership
        if appeal.appellant_pk != user_pk:
            return False, "You can only withdraw your own appeals"

        # Check if appeal can be withdrawn
        if appeal.status not in [AppealStatus.PENDING, AppealStatus.UNDER_REVIEW]:
            return False, f"Cannot withdraw appeal with status: {appeal.status.value}"

        # Update status to withdrawn
        update_data = AppealUpdate(
            status=AppealStatus.WITHDRAWN,
            reviewed_by=None,
            review_notes=None,
            decision_reason=None,
        )
        await self.appeal_repository.update_appeal(appeal_pk, update_data)

        # Remove from queue if still pending
        if appeal.status == AppealStatus.PENDING:
            await self.queue_service.remove_appeal_from_queue(appeal_pk)

        return True, ""

    async def get_appeals_queue(
        self,
        status: AppealStatus = AppealStatus.PENDING,
        page: int = 1,
        page_size: int = 50,
    ) -> AppealResponse:
        """Get appeals queue for moderators."""
        offset = (page - 1) * page_size

        appeals = await self.appeal_repository.get_appeals_queue(
            status, priority_order=True, limit=page_size, offset=offset
        )

        # Count total appeals with this status
        total_count = await self.appeal_repository.count("status = $1", [status.value])

        return AppealResponse(
            appeals=appeals,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total_count,
            has_previous=page > 1,
        )

    async def assign_appeal_for_review(
        self, appeal_pk: UUID, reviewer_pk: UUID
    ) -> tuple[bool, str]:
        """
        Assign an appeal to a reviewer (moderator/admin).

        Returns:
            Tuple of (success, error_message)
        """
        # Get the appeal
        appeal = await self.appeal_repository.get(appeal_pk)
        if not appeal:
            return False, "Appeal not found"

        # Check if appeal is in pending status
        if appeal.status != AppealStatus.PENDING:
            return False, f"Appeal is not pending (status: {appeal.status.value})"

        # Update appeal to under review
        update_data = AppealUpdate(
            status=AppealStatus.UNDER_REVIEW,
            reviewed_by=reviewer_pk,
            review_notes=None,
            decision_reason=None,
        )

        await self.appeal_repository.update_appeal(appeal_pk, update_data)
        return True, ""

    async def decide_appeal(
        self,
        appeal_pk: UUID,
        reviewer_pk: UUID,
        decision: AppealStatus,
        decision_data: AppealDecision,
    ) -> tuple[bool, str]:
        """
        Make a decision on an appeal (sustain or deny).

        Returns:
            Tuple of (success, error_message)
        """
        if decision not in [AppealStatus.SUSTAINED, AppealStatus.DENIED]:
            return False, "Decision must be either SUSTAINED or DENIED"

        # Get the appeal
        appeal = await self.appeal_repository.get(appeal_pk)
        if not appeal:
            return False, "Appeal not found"

        # Verify reviewer is assigned to this appeal
        if appeal.reviewed_by != reviewer_pk:
            return False, "You are not assigned to review this appeal"

        # Check if appeal is under review
        if appeal.status != AppealStatus.UNDER_REVIEW:
            return False, f"Appeal is not under review (status: {appeal.status.value})"

        # Update appeal with decision
        now = datetime.now(UTC)
        update_data = AppealUpdate(
            status=decision,
            decision_reason=decision_data.decision_reason,
            review_notes=decision_data.review_notes,
            reviewed_at=now,
            reviewed_by=reviewer_pk,
        )

        await self.appeal_repository.update_appeal(appeal_pk, update_data)

        # Process the decision consequences
        await self._process_appeal_decision(appeal, decision, reviewer_pk)

        return True, ""

    async def get_appeal_statistics(self) -> AppealStats:
        """Get appeal statistics for moderators."""
        return await self.appeal_repository.get_appeal_statistics()

    async def get_appeal_by_id(self, appeal_pk: UUID) -> AppealWithContent | None:
        """Get a specific appeal with content details."""
        appeals = await self.appeal_repository.get_appeals_queue(
            status=AppealStatus.PENDING, priority_order=False, limit=1, offset=0
        )

        # This is a simplified approach - in production, you'd want a dedicated method
        # that can fetch a single appeal by ID with content details
        for appeal in appeals:
            if appeal.pk == appeal_pk:
                return appeal

        return None

    async def _process_appeal_decision(
        self, appeal: Appeal, decision: AppealStatus, reviewer_pk: UUID
    ) -> None:
        """Process the consequences of an appeal decision."""
        if decision == AppealStatus.SUSTAINED:
            await self._process_sustained_appeal(appeal)
        elif decision == AppealStatus.DENIED:
            await self._process_denied_appeal(appeal)

    async def _process_sustained_appeal(self, appeal: Appeal) -> None:
        """
        Process a sustained (granted) appeal.

        This involves:
        1. Reversing the original moderation decision
        2. Awarding loyalty points to the appellant
        3. Potentially penalizing the original moderator
        """
        # Award loyalty points for successful appeal
        await self.loyalty_score_service.record_appeal_outcome(
            user_pk=appeal.appellant_pk,
            appeal_pk=appeal.pk,
            outcome="sustained",
            points_awarded=50,  # Configurable
        )

        # TODO(josh): Implement content restoration logic
        # This would involve:
        # - Restoring rejected/removed content
        # - Updating content status
        # - Notifying relevant parties

        # TODO(josh): Consider moderator feedback/training
        # Track moderation accuracy for quality improvement

    async def _process_denied_appeal(self, appeal: Appeal) -> None:
        """
        Process a denied appeal.

        This involves:
        1. Potentially penalizing the appellant for frivolous appeals
        2. Recording the decision for future reference
        """
        # Small penalty for denied appeals to discourage frivolous appeals
        await self.loyalty_score_service.record_appeal_outcome(
            user_pk=appeal.appellant_pk,
            appeal_pk=appeal.pk,
            outcome="denied",
            points_awarded=-5,  # Small penalty
        )

    async def get_appealable_content(
        self, user_pk: UUID, content_type: ContentType, content_pk: UUID
    ) -> dict | None:
        """
        Get content details for appeal submission.

        Returns basic content information if the content exists and is appealable.
        """
        # This would fetch content details from the appropriate repository
        # For now, return a placeholder structure
        return {
            "content_type": content_type.value,
            "content_pk": str(content_pk),
            "title": "Content Title",  # Would be fetched from DB
            "excerpt": "Content excerpt...",  # Would be fetched from DB
            "moderated_at": datetime.now(UTC),  # Would be fetched from DB
            "moderation_reason": "Violation of community guidelines",  # From DB
        }
