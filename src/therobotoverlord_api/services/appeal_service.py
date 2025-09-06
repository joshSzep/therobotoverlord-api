"""Appeal service for The Robot Overlord API."""

import logging

from datetime import UTC
from datetime import datetime
from typing import Any
from uuid import UUID

from therobotoverlord_api.database.models.appeal import Appeal
from therobotoverlord_api.database.models.appeal import AppealCreate
from therobotoverlord_api.database.models.appeal import AppealDecision
from therobotoverlord_api.database.models.appeal import AppealEligibility
from therobotoverlord_api.database.models.appeal import AppealResponse
from therobotoverlord_api.database.models.appeal import AppealStats
from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal import AppealType
from therobotoverlord_api.database.models.appeal import AppealUpdate
from therobotoverlord_api.database.models.appeal import AppealWithContent
from therobotoverlord_api.database.models.appeal_history import AppealHistoryAction
from therobotoverlord_api.database.models.appeal_history import AppealHistoryCreate
from therobotoverlord_api.database.models.appeal_history import AppealHistoryEntry
from therobotoverlord_api.database.models.appeal_history import AppealStatusSummary
from therobotoverlord_api.database.models.appeal_with_editing import (
    AppealDecisionWithEdit,
)
from therobotoverlord_api.database.models.appeal_with_editing import (
    AppealUpdateWithRestoration,
)
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.repositories.appeal import AppealRepository
from therobotoverlord_api.database.repositories.appeal_history_repository import (
    AppealHistoryRepository,
)
from therobotoverlord_api.services.content_restoration_service import (
    ContentRestorationService,
)
from therobotoverlord_api.services.loyalty_score_service import LoyaltyScoreService
from therobotoverlord_api.services.queue_service import QueueService
from therobotoverlord_api.websocket.manager import WebSocketManager
from therobotoverlord_api.websocket.models import WebSocketEventType
from therobotoverlord_api.websocket.models import WebSocketMessage

logger = logging.getLogger(__name__)


class AppealService:
    """Service for managing appeals workflow."""

    def __init__(self):
        """Initialize the appeal service."""
        self.appeal_repository = AppealRepository()
        self.appeal_history_repository = AppealHistoryRepository()
        self.queue_service = QueueService()
        self.websocket_manager = WebSocketManager()
        self.loyalty_score_service = LoyaltyScoreService()
        self.content_restoration_service = ContentRestorationService()
        self._rate_limit_cache: dict[UUID, datetime] = {}

    async def submit_appeal(
        self, user_pk: UUID, appeal_data: AppealCreate
    ) -> tuple[Appeal | None, str]:
        """
        Submit a new appeal with rate limiting.

        Returns:
            Tuple of (Appeal, error_message). Appeal is None if submission failed.
        """
        # Check rate limiting (1 appeal per 5 minutes per user)
        if not await self._check_rate_limit(user_pk):
            return (
                None,
                "Rate limit exceeded. You can only submit one appeal every 5 minutes.",
            )

        # Verify content type and pk are valid
        if not appeal_data.content_type or not appeal_data.content_pk:
            return None, "Invalid appeal type or content pk"

        # Check eligibility
        eligibility = await self.check_appeal_eligibility(
            user_pk, appeal_data.content_type, appeal_data.content_pk
        )

        if not eligibility.eligible:
            return None, eligibility.reason or "Appeal not eligible"

        # Create the appeal
        appeal = await self.appeal_repository.create_appeal(appeal_data, user_pk)

        # Update rate limit cache
        self._rate_limit_cache[user_pk] = datetime.now(UTC)

        # Add to appeals queue for processing
        await self.queue_service.add_appeal_to_queue(appeal.pk)

        # Send WebSocket notification to moderators
        await self.websocket_manager.broadcast_to_channel(
            "moderator",
            WebSocketMessage(
                event_type=WebSocketEventType.NEW_APPEAL,
                data={
                    "appeal_id": str(appeal.pk),
                    "appeal_type": appeal_data.appeal_type.value,
                    "content_type": appeal_data.content_type.value
                    if appeal_data.content_type
                    else None,
                    "content_pk": str(appeal_data.content_pk)
                    if appeal_data.content_pk
                    else None,
                },
            ),
        )

        logger.info(f"Appeal {appeal.pk} submitted by user {user_pk}")
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
        if appeal.user_pk != user_pk:
            return False, "You can only withdraw your own appeals"

        # Check if appeal can be withdrawn
        if appeal.status not in [AppealStatus.PENDING, AppealStatus.UNDER_REVIEW]:
            return False, f"Cannot withdraw appeal with status: {appeal.status.value}"

        # Update status to denied (withdrawn appeals are marked as denied)
        update_data = AppealUpdate(
            status=AppealStatus.DENIED,
            reviewed_by=None,
            review_notes=None,
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
            return False, f"Appeal is not under review (status: {appeal.status})"

        # Update appeal with decision
        now = datetime.now(UTC)
        update_data = AppealUpdate(
            status=decision,
            review_notes=decision_data.review_notes,
            reviewed_at=now,
            reviewed_by=reviewer_pk,
        )

        await self.appeal_repository.update_appeal(appeal_pk, update_data)

        # Process the decision consequences
        await self._process_appeal_decision(appeal, decision, reviewer_pk)

        # Send WebSocket notification to appellant
        await self._send_appeal_outcome_notification(appeal, decision)

        return True, ""

    async def decide_appeal_with_edit(
        self,
        appeal_pk: UUID,
        reviewer_pk: UUID,
        decision: AppealStatus,
        decision_data: AppealDecisionWithEdit,
        edited_content: dict[str, str | None] | None = None,
    ) -> tuple[bool, str]:
        """Make a decision on an appeal with optional content editing."""

        if decision not in [AppealStatus.SUSTAINED, AppealStatus.DENIED]:
            return False, "Decision must be either SUSTAINED or DENIED"

        # Get the appeal
        appeal = await self.appeal_repository.get(appeal_pk)
        if not appeal:
            return False, "Appeal not found"

        # Verify reviewer assignment and status
        if appeal.reviewed_by != reviewer_pk:
            return False, "You are not assigned to review this appeal"

        if appeal.status != AppealStatus.UNDER_REVIEW:
            return False, f"Appeal is not under review (status: {appeal.status})"

        # Update appeal with decision
        now = datetime.now(UTC)
        update_data = AppealUpdate(
            status=decision,
            review_notes=decision_data.review_notes,
            reviewed_at=now,
            reviewed_by=reviewer_pk,
        )

        await self.appeal_repository.update_appeal(appeal_pk, update_data)

        # Process the decision with editing capability
        if decision == AppealStatus.SUSTAINED:
            await self._process_sustained_appeal_with_edit(
                appeal,
                reviewer_pk,
                edited_content,
                decision_data.edit_reason,
                decision_data.review_notes,
            )
        elif decision == AppealStatus.DENIED:
            await self._process_denied_appeal(appeal)

        # Send WebSocket notification to appellant
        await self._send_appeal_outcome_notification(appeal, decision)

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
            user_pk=appeal.user_pk,
            appeal_pk=appeal.pk,
            outcome="sustained",
            points_awarded=50,  # Configurable
        )

        logger.info(f"Content restoration for appeal {appeal.pk} not yet implemented")

        # TODO(josh): Consider moderator feedback/training
        # Track moderation accuracy for quality improvement

    async def _process_sustained_appeal_with_edit(
        self,
        appeal: Appeal,
        reviewer_pk: UUID,
        edited_content: dict[str, str | None] | None = None,
        edit_reason: str | None = None,
        review_notes: str | None = None,
    ) -> None:
        """Process a sustained appeal with optional content editing."""

        # 1. Award loyalty points (existing)
        await self.loyalty_score_service.record_appeal_outcome(
            user_pk=appeal.user_pk,
            appeal_pk=appeal.pk,
            outcome="sustained",
            points_awarded=50,
        )

        # 2. Restore content with edits (NEW)
        # Determine content type and pk based on appeal type
        if appeal.appeal_type == AppealType.FLAG_APPEAL:
            content_type = ContentType.POST
            content_pk = appeal.flag_pk
        elif appeal.appeal_type == AppealType.SANCTION_APPEAL:
            content_type = ContentType.POST  # Sanctions are typically on posts
            content_pk = appeal.sanction_pk
        else:
            content_type = ContentType.POST
            content_pk = appeal.flag_pk or appeal.sanction_pk

        # Validate content type and pk
        if not content_type or not content_pk:
            raise ValueError("Invalid appeal type or content pk")

        restoration_result = await self.content_restoration_service.restore_with_edits(
            content_type=content_type,
            content_pk=content_pk,
            appeal=appeal,
            reviewer_pk=reviewer_pk,
            edited_content=edited_content,
            edit_reason=edit_reason,
        )

        # 3. Update appeal with restoration info
        if restoration_result.success:
            update_data = AppealUpdateWithRestoration(
                review_notes=review_notes,
                restoration_completed=True,
                restoration_completed_at=datetime.now(UTC).isoformat(),
                restoration_metadata={
                    "content_edited": bool(edited_content),
                    "version_pk": str(restoration_result.version_pk)
                    if restoration_result.version_pk
                    else None,
                    "restoration_pk": str(restoration_result.restoration_pk)
                    if restoration_result.restoration_pk
                    else None,
                },
            )

            # Update appeal record with restoration metadata
            await self.appeal_repository.update_from_dict(
                appeal.pk, update_data.model_dump(exclude_none=True)
            )

        # 4. Send notifications about restoration and any edits
        # TODO(josh): Implement notification service integration

    async def _process_denied_appeal(self, appeal: Appeal) -> None:
        """
        Process a denied appeal.

        This involves:
        1. Potentially penalizing the appellant for frivolous appeals
        2. Recording the decision for future reference
        """
        # Small penalty for denied appeals to discourage frivolous appeals
        await self.loyalty_score_service.record_appeal_outcome(
            user_pk=appeal.user_pk,
            appeal_pk=appeal.pk,
            outcome="denied",
            points_awarded=-5,  # Small penalty
        )

        # Apply sanctions for repeated denied appeals
        await self._apply_sanctions_for_denied_appeal(appeal)

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

    async def _check_rate_limit(self, user_pk: UUID) -> bool:
        """Check if user has exceeded rate limit for appeal submissions."""
        last_submission = self._rate_limit_cache.get(user_pk)
        if not last_submission:
            return True

        # 5 minutes = 300 seconds
        time_since_last = (datetime.now(UTC) - last_submission).total_seconds()
        return time_since_last >= 300

    async def _send_appeal_outcome_notification(
        self, appeal: Appeal, decision: AppealStatus
    ) -> None:
        """Send WebSocket notification to appellant about appeal outcome."""
        try:
            await self.websocket_manager.send_to_user(
                appeal.user_pk,
                WebSocketMessage(
                    event_type=WebSocketEventType.APPEAL_OUTCOME,
                    data={
                        "appeal_id": str(appeal.pk),
                        "decision": decision.value,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                ),
            )
            logger.info(f"Sent appeal outcome notification for appeal {appeal.pk}")
        except Exception:
            logger.exception(
                f"Failed to send appeal outcome notification for appeal {appeal.pk}"
            )

    async def _apply_sanctions_for_denied_appeal(self, appeal: Appeal) -> None:
        """Apply sanctions if user has too many denied appeals."""
        try:
            # Count denied appeals in the last 30 days
            from datetime import timedelta

            cutoff_date = datetime.now(UTC) - timedelta(days=30)

            denied_count = (
                await self.appeal_repository.count_user_appeals_by_status_since(
                    appeal.user_pk, AppealStatus.DENIED, cutoff_date
                )
            )

            # Apply escalating sanctions
            if denied_count >= 5:  # 5+ denied appeals in 30 days
                # Apply temporary ban from submitting appeals
                await self._apply_appeal_ban(appeal.user_pk, days=7)
                logger.warning(
                    f"Applied 7-day appeal ban to user {appeal.user_pk} for {denied_count} denied appeals"
                )
            elif denied_count >= 3:  # 3+ denied appeals in 30 days
                # Apply warning and reduced loyalty score
                await self.loyalty_score_service.record_appeal_outcome(
                    user_pk=appeal.user_pk,
                    appeal_pk=appeal.pk,
                    outcome="frivolous_appeal_penalty",
                    points_awarded=-25,
                )
                logger.info(
                    f"Applied frivolous appeal penalty to user {appeal.user_pk}"
                )

        except Exception:
            logger.exception(f"Failed to apply sanctions for denied appeal {appeal.pk}")

    async def _apply_appeal_ban(self, user_pk: UUID, days: int) -> None:
        """Apply temporary ban from submitting appeals."""
        # This would integrate with the sanctions system
        # For now, just log the action
        logger.info(f"Would apply {days}-day appeal ban to user {user_pk}")
        # TODO(josh): Integrate with sanctions service to apply actual ban

    # Appeal History Methods
    async def get_appeal_history(self, appeal_pk: UUID) -> list[AppealHistoryEntry]:
        """Get complete history for an appeal."""
        return await self.appeal_history_repository.get_appeal_history(appeal_pk)

    async def get_user_appeal_history(
        self, user_pk: UUID, limit: int = 50
    ) -> list[AppealHistoryEntry]:
        """Get appeal history for a specific user."""
        return await self.appeal_history_repository.get_user_appeal_history(
            user_pk, limit
        )

    async def get_appeal_status_summary(
        self, appeal_pk: UUID
    ) -> AppealStatusSummary | None:
        """Get status summary for an appeal."""
        return await self.appeal_history_repository.get_appeal_status_summary(appeal_pk)

    async def _log_appeal_action(
        self,
        appeal_pk: UUID,
        action: AppealHistoryAction,
        actor_pk: UUID | None = None,
        details: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> None:
        """Log an appeal action to history."""
        history_entry = AppealHistoryCreate(
            appeal_pk=appeal_pk,
            action=action,
            actor_pk=actor_pk,
            details=details,
            notes=notes,
        )
        await self.appeal_history_repository.create_history_entry(history_entry)
