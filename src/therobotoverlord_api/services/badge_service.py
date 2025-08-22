"""Badge service for The Robot Overlord API."""

import logging

from uuid import UUID

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.badge import Badge
from therobotoverlord_api.database.models.badge import BadgeCreate
from therobotoverlord_api.database.models.badge import BadgeEligibilityCheck
from therobotoverlord_api.database.models.badge import BadgeUpdate
from therobotoverlord_api.database.models.badge import UserBadge
from therobotoverlord_api.database.models.badge import UserBadgeCreate
from therobotoverlord_api.database.models.badge import UserBadgeSummary
from therobotoverlord_api.database.models.badge import UserBadgeWithDetails
from therobotoverlord_api.database.repositories.badge import BadgeRepository
from therobotoverlord_api.database.repositories.badge import UserBadgeRepository

logger = logging.getLogger(__name__)


class BadgeService:
    """Service for badge management and awarding logic."""

    def __init__(self):
        self.badge_repo = BadgeRepository()
        self.user_badge_repo = UserBadgeRepository()

    # Badge Management
    async def get_all_badges(self) -> list[Badge]:
        """Get all active badges."""
        return await self.badge_repo.get_active_badges()

    async def get_badge_by_id(self, badge_id: UUID) -> Badge | None:
        """Get badge by ID."""
        return await self.badge_repo.get_by_pk(badge_id)

    async def get_badge_by_name(self, name: str) -> Badge | None:
        """Get badge by name."""
        return await self.badge_repo.get_by_name(name)

    async def create_badge(self, badge_data: BadgeCreate) -> Badge:
        """Create a new badge."""
        badge_dict = badge_data.model_dump()
        return await self.badge_repo.create_from_dict(badge_dict)

    async def update_badge(
        self, badge_id: UUID, badge_data: BadgeUpdate
    ) -> Badge | None:
        """Update a badge."""
        update_dict = {
            k: v for k, v in badge_data.model_dump().items() if v is not None
        }
        if not update_dict:
            return await self.badge_repo.get_by_pk(badge_id)
        return await self.badge_repo.update_from_dict(badge_id, update_dict)

    async def delete_badge(self, badge_id: UUID) -> bool:
        """Delete a badge (soft delete by setting is_active=False)."""
        return (
            await self.badge_repo.update_from_dict(badge_id, {"is_active": False})
            is not None
        )

    # User Badge Management
    async def get_user_badges(self, user_id: UUID) -> list[UserBadgeWithDetails]:
        """Get all badges for a user."""
        return await self.user_badge_repo.get_user_badges(user_id)

    async def get_user_badge_summary(
        self, user_id: UUID, username: str
    ) -> UserBadgeSummary:
        """Get badge summary for a user."""
        badges = await self.user_badge_repo.get_user_badges(user_id)
        counts = await self.user_badge_repo.get_user_badge_counts(user_id)
        recent_badges = await self.user_badge_repo.get_recent_user_badges(user_id, 3)

        return UserBadgeSummary(
            user_pk=user_id,
            username=username,
            total_badges=counts["total"],
            positive_badges=counts["positive"],
            negative_badges=counts["negative"],
            recent_badges=recent_badges,
        )

    async def manually_award_badge(
        self,
        user_id: UUID,
        badge_id: UUID,
        awarded_by_user_id: UUID,
        awarded_for_post_id: UUID | None = None,
        awarded_for_topic_id: UUID | None = None,
    ) -> UserBadge | None:
        """Manually award a badge to a user (admin function)."""
        # Check if user already has this badge
        if await self.user_badge_repo.has_badge(user_id, badge_id):
            return None

        # Check if badge exists and is active
        badge = await self.badge_repo.get_by_pk(badge_id)
        if not badge or not badge.is_active:
            return None

        user_badge_data = UserBadgeCreate(
            user_pk=user_id,
            badge_pk=badge_id,
            awarded_for_post_pk=awarded_for_post_id,
            awarded_for_topic_pk=awarded_for_topic_id,
            awarded_by_event=f"manual_award_by_{awarded_by_user_id}",
        )

        user_badge = await self.user_badge_repo.award_badge(user_badge_data.model_dump())
        
        # Broadcast badge earned notification via WebSocket
        if user_badge:
            from therobotoverlord_api.websocket.events import get_event_broadcaster
            from therobotoverlord_api.websocket.manager import websocket_manager
            
            event_broadcaster = get_event_broadcaster(websocket_manager)
            await event_broadcaster.broadcast_badge_earned(
                user_id=user_id,
                badge_id=badge_id,
                badge_name=badge.name,
                badge_description=badge.description,
                badge_icon=badge.image_url,
            )
        
        return user_badge

    async def revoke_badge(self, user_id: UUID, badge_id: UUID) -> bool:
        """Revoke a badge from a user."""
        user_badge = await self.user_badge_repo.find_one_by(
            user_pk=user_id, badge_pk=badge_id
        )
        if not user_badge:
            return False

        return await self.user_badge_repo.delete_by_pk(user_badge.pk)

    # Badge Eligibility and Automatic Awarding
    async def evaluate_badge_criteria_for_user(
        self, user_id: UUID
    ) -> list[BadgeEligibilityCheck]:
        """Evaluate all badge criteria for a user and return eligibility status."""
        badges = await self.badge_repo.get_active_badges()
        eligibility_checks = []

        for badge in badges:
            # Skip if user already has this badge
            if await self.user_badge_repo.has_badge(user_id, badge.pk):
                continue

            eligibility = await self._check_badge_eligibility(user_id, badge)
            eligibility_checks.append(eligibility)

        return eligibility_checks

    async def _check_badge_eligibility(
        self, user_id: UUID, badge: Badge
    ) -> BadgeEligibilityCheck:
        """Check if a user is eligible for a specific badge."""
        criteria = badge.criteria_config
        criteria_type = criteria.get("type")

        if criteria_type == "approved_posts":
            return await self._check_approved_posts_criteria(user_id, badge, criteria)
        if criteria_type == "rejected_posts":
            return await self._check_rejected_posts_criteria(user_id, badge, criteria)
        if criteria_type == "successful_appeals":
            return await self._check_successful_appeals_criteria(
                user_id, badge, criteria
            )
        if criteria_type == "first_approved_post":
            return await self._check_first_approved_post_criteria(user_id, badge)

        return BadgeEligibilityCheck(
            badge_pk=badge.pk,
            badge_name=badge.name,
            is_eligible=False,
            current_progress=0,
            required_progress=0,
            criteria_met=False,
            reason="Unknown criteria type",
        )

    async def _check_approved_posts_criteria(
        self, user_id: UUID, badge: Badge, criteria: dict
    ) -> BadgeEligibilityCheck:
        """Check approved posts criteria."""
        required_count = criteria.get("count", 1)
        criteria_filter = criteria.get("criteria")

        query = """
            SELECT COUNT(*)
            FROM moderation_events me
            WHERE me.user_id = $1
            AND me.content_type = 'post'
            AND me.outcome = 'approved'
        """
        params = [user_id]

        # Add specific criteria filters if specified
        if criteria_filter == "logic_heavy":
            # This would need to be implemented based on your moderation feedback system
            # For now, we'll count all approved posts
            pass
        elif criteria_filter == "well_sourced":
            # Similar - would need moderation feedback analysis
            pass

        async with get_db_connection() as connection:
            current_count = await connection.fetchval(query, *params) or 0

        return BadgeEligibilityCheck(
            badge_pk=badge.pk,
            badge_name=badge.name,
            is_eligible=current_count >= required_count,
            current_progress=current_count,
            required_progress=required_count,
            criteria_met=current_count >= required_count,
            reason=f"Has {current_count} approved posts, needs {required_count}",
        )

    async def _check_rejected_posts_criteria(
        self, user_id: UUID, badge: Badge, criteria: dict
    ) -> BadgeEligibilityCheck:
        """Check rejected posts criteria."""
        required_count = criteria.get("count", 1)
        criteria_filter = criteria.get("criteria")

        query = """
            SELECT COUNT(*)
            FROM moderation_events me
            WHERE me.user_id = $1
            AND me.content_type = 'post'
            AND me.outcome = 'rejected'
        """
        params = [user_id]

        # Add specific criteria filters based on rejection reasons
        if criteria_filter in ["strawman_fallacy", "ad_hominem", "poor_logic"]:
            query += " AND EXISTS (SELECT 1 FROM posts p WHERE p.pk = me.content_id AND p.rejection_reason = $2)"
            params.append(criteria_filter)

        async with get_db_connection() as connection:
            current_count = await connection.fetchval(query, *params) or 0

        return BadgeEligibilityCheck(
            badge_pk=badge.pk,
            badge_name=badge.name,
            is_eligible=current_count >= required_count,
            current_progress=current_count,
            required_progress=required_count,
            criteria_met=current_count >= required_count,
            reason=f"Has {current_count} rejected posts with {criteria_filter}, needs {required_count}",
        )

    async def _check_successful_appeals_criteria(
        self, user_id: UUID, badge: Badge, criteria: dict
    ) -> BadgeEligibilityCheck:
        """Check successful appeals criteria."""
        required_count = criteria.get("count", 1)

        query = """
            SELECT COUNT(*)
            FROM appeals a
            WHERE a.appellant_id = $1
            AND a.status = 'sustained'
        """

        async with get_db_connection() as connection:
            current_count = await connection.fetchval(query, user_id) or 0

        return BadgeEligibilityCheck(
            badge_pk=badge.pk,
            badge_name=badge.name,
            is_eligible=current_count >= required_count,
            current_progress=current_count,
            required_progress=required_count,
            criteria_met=current_count >= required_count,
            reason=f"Has {current_count} successful appeals, needs {required_count}",
        )

    async def _check_first_approved_post_criteria(
        self, user_id: UUID, badge: Badge
    ) -> BadgeEligibilityCheck:
        """Check first approved post criteria."""
        query = """
            SELECT COUNT(*)
            FROM moderation_events me
            WHERE me.user_id = $1
            AND me.content_type = 'post'
            AND me.outcome = 'approved'
            LIMIT 1
        """

        async with get_db_connection() as connection:
            result = await connection.fetchval(query, user_id)
            has_approved_post = (result or 0) > 0

        return BadgeEligibilityCheck(
            badge_pk=badge.pk,
            badge_name=badge.name,
            is_eligible=has_approved_post,
            current_progress=1 if has_approved_post else 0,
            required_progress=1,
            criteria_met=has_approved_post,
            reason="Has first approved post"
            if has_approved_post
            else "No approved posts yet",
        )

    async def auto_award_eligible_badges(
        self, user_id: UUID, event_type: str
    ) -> list[UserBadge]:
        """Automatically award badges that the user is now eligible for."""
        eligibility_checks = await self.evaluate_badge_criteria_for_user(user_id)
        awarded_badges = []

        for check in eligibility_checks:
            if check.is_eligible:
                user_badge_data = UserBadgeCreate(
                    user_pk=user_id,
                    badge_pk=check.badge_pk,
                    awarded_by_event=event_type,
                )

                try:
                    awarded_badge = await self.user_badge_repo.award_badge(
                        user_badge_data.model_dump()
                    )
                    awarded_badges.append(awarded_badge)
                except Exception as e:  # nosec B112
                    # Badge might have been awarded by another process (race condition)
                    # This is expected behavior for concurrent badge awarding
                    logger.debug(
                        f"Badge {check.badge_pk} already awarded to user {user_id}: {e}"
                    )
                    continue

        return awarded_badges

    async def get_badge_recipients(
        self, badge_id: UUID, limit: int = 100
    ) -> list[UserBadgeWithDetails]:
        """Get users who have received a specific badge."""
        return await self.user_badge_repo.get_badge_recipients(badge_id, limit)
