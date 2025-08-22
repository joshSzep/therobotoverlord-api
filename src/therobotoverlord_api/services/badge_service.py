"""Badge service for managing user badges and badge eligibility."""

import logging

from uuid import UUID

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.badge import Badge
from therobotoverlord_api.database.models.badge import BadgeEligibilityCheck
from therobotoverlord_api.database.models.badge import UserBadge
from therobotoverlord_api.database.models.badge import UserBadgeCreate
from therobotoverlord_api.database.models.badge import UserBadgeWithDetails
from therobotoverlord_api.database.repositories.badge import BadgeRepository
from therobotoverlord_api.database.repositories.badge import UserBadgeRepository
from therobotoverlord_api.websocket.events import get_event_broadcaster
from therobotoverlord_api.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)


class BadgeService:
    """Service for managing badges and user badge awards."""

    def __init__(self):
        self.badge_repo = BadgeRepository()
        self.user_badge_repo = UserBadgeRepository()

    # Badge Management
    async def get_all_badges(self, *, active_only: bool = True) -> list[Badge]:
        """Get all badges, optionally filtered by active status."""
        if active_only:
            return await self.badge_repo.get_active_badges()
        return await self.badge_repo.get_all()

    async def get_badge_by_id(self, badge_id: UUID) -> Badge | None:
        """Get a specific badge by ID."""
        return await self.badge_repo.get_by_pk(badge_id)

    async def get_badge_by_name(self, name: str) -> Badge | None:
        """Get badge by name."""
        return await self.badge_repo.get_by_name(name)

    async def create_badge(self, badge_data) -> Badge:
        """Create a new badge."""
        if hasattr(badge_data, "model_dump"):
            badge_dict = badge_data.model_dump()
        else:
            badge_dict = badge_data
        return await self.badge_repo.create_from_dict(badge_dict)

    async def update_badge(self, badge_id: UUID, badge_data) -> Badge | None:
        """Update an existing badge."""
        if hasattr(badge_data, "model_dump"):
            update_dict = {
                k: v for k, v in badge_data.model_dump().items() if v is not None
            }
            if not update_dict:
                return await self.badge_repo.get_by_pk(badge_id)
        else:
            update_dict = badge_data
        return await self.badge_repo.update_from_dict(badge_id, update_dict)

    async def delete_badge(self, badge_id: UUID) -> bool:
        """Delete a badge (soft delete by setting is_active=False)."""
        result = await self.badge_repo.update_from_dict(badge_id, {"is_active": False})
        return result is not None

    # User Badge Management
    async def get_user_badges(
        self, user_id: UUID, *, include_details: bool = False
    ) -> list[UserBadge | UserBadgeWithDetails]:
        """Get all badges for a specific user."""
        if include_details:
            return await self.user_badge_repo.get_user_badges_with_details(user_id)
        return await self.user_badge_repo.get_user_badges(user_id)

    async def get_user_badge_summary(self, user_id: UUID, username: str):
        """Get badge summary for a user."""
        from therobotoverlord_api.database.models.badge import UserBadgeSummary

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

    async def award_badge(
        self,
        user_id: UUID,
        badge_id: UUID,
        awarded_by_event: str = "manual",
        websocket_manager: WebSocketManager | None = None,
    ) -> UserBadge | None:
        """Award a badge to a user."""
        # Check if user already has this badge
        if await self.user_badge_repo.has_badge(user_id, badge_id):
            logger.warning(f"User {user_id} already has badge {badge_id}")
            return None

        # Create user badge record
        user_badge_data = UserBadgeCreate(
            user_pk=user_id,
            badge_pk=badge_id,
            awarded_by_event=awarded_by_event,
        )

        user_badge = await self.user_badge_repo.create(user_badge_data.model_dump())

        # Broadcast badge earned notification via WebSocket
        if websocket_manager and user_badge:
            badge = await self.badge_repo.get_by_pk(badge_id)
            if badge:
                try:
                    broadcaster = get_event_broadcaster(websocket_manager)
                    await broadcaster.broadcast_badge_earned(
                        user_id=user_id,
                        badge_id=badge_id,
                        badge_name=badge.name,
                        badge_description=badge.description,
                        badge_icon=badge.image_url,
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast badge earned event: {e}")

        return user_badge

    async def revoke_badge(self, user_id: UUID, badge_id: UUID) -> bool:
        """Revoke a badge from a user."""
        user_badge = await self.user_badge_repo.find_one_by(
            user_pk=user_id, badge_pk=badge_id
        )
        if not user_badge:
            return False

        return await self.user_badge_repo.delete_by_pk(user_badge.pk)

    async def manually_award_badge(
        self,
        user_id: UUID,
        badge_id: UUID,
        awarded_by_user_id: UUID,
        awarded_for_post_id: UUID | None = None,
        awarded_for_topic_id: UUID | None = None,
        websocket_manager: WebSocketManager | None = None,
    ) -> UserBadge | None:
        """Manually award a badge to a user."""
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

        user_badge = await self.user_badge_repo.award_badge(
            user_badge_data.model_dump()
        )

        # Broadcast badge earned notification via WebSocket
        if websocket_manager and user_badge:
            try:
                broadcaster = get_event_broadcaster(websocket_manager)
                await broadcaster.broadcast_badge_earned(
                    user_id=user_id,
                    badge_id=badge_id,
                    badge_name=badge.name,
                    badge_description=badge.description,
                    badge_icon=badge.image_url,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast badge earned event: {e}")

        return user_badge

    # Badge Eligibility and Automatic Awarding
    async def evaluate_badge_criteria_for_user(
        self, user_id: UUID, websocket_manager: WebSocketManager | None = None
    ) -> list[BadgeEligibilityCheck]:
        """Evaluate badge criteria for a user and return eligibility checks."""
        try:
            badges = await self.badge_repo.get_active_badges()
            eligibility_checks = []

            for badge in badges:
                # Check if user already has this badge
                has_badge = await self.user_badge_repo.has_badge(user_id, badge.pk)
                if has_badge:
                    continue

                # Check badge eligibility with detailed criteria
                eligibility_check = await self._check_badge_eligibility(user_id, badge)
                criteria_met = eligibility_check.criteria_met

                # Only add eligible badges to the list
                if criteria_met:
                    eligibility_checks.append(eligibility_check)

                    # Award badge if criteria met
                    try:
                        user_badge_data = UserBadgeCreate(
                            user_pk=user_id,
                            badge_pk=badge.pk,
                            awarded_by_event="auto_award",
                        )
                        await self.user_badge_repo.award_badge(
                            user_badge_data.model_dump()
                        )

                        # Broadcast badge earned event
                        if websocket_manager:
                            try:
                                broadcaster = get_event_broadcaster(websocket_manager)
                                await broadcaster.broadcast_badge_earned(
                                    user_id=user_id,
                                    badge_id=badge.pk,
                                    badge_name=badge.name,
                                    badge_description=badge.description,
                                    badge_icon=badge.image_url,
                                )
                            except Exception as ws_error:
                                logger.warning(
                                    f"Failed to broadcast badge earned event: {ws_error}"
                                )
                    except Exception as award_error:
                        logger.error(
                            f"Failed to award badge {badge.pk} to user {user_id}: {award_error}"
                        )

            return eligibility_checks

        except Exception as e:
            logger.error(f"Error evaluating badge criteria for user {user_id}: {e}")
            return []

    async def _evaluate_badge_criteria(
        self, user_id: UUID, criteria_config: dict
    ) -> bool:
        """Evaluate if user meets badge criteria (simplified for testing)."""
        # This is a simplified version for testing purposes
        # In reality, this would check specific badge criteria
        return True

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

    async def evaluate_badge_criteria(
        self, user_id: UUID, websocket_manager=None
    ) -> list[BadgeEligibilityCheck]:
        """Evaluate badge criteria and optionally broadcast results."""
        eligibility_checks = await self.evaluate_badge_criteria_for_user(user_id)

        # Broadcast badge eligibility updates if websocket_manager provided
        if websocket_manager and eligibility_checks:
            event_broadcaster = get_event_broadcaster(websocket_manager)
            for check in eligibility_checks:
                if check.is_eligible:
                    # This would broadcast badge eligibility notification
                    # Implementation depends on specific requirements
                    pass

        return eligibility_checks

    async def auto_award_eligible_badges(
        self, user_id: UUID, event_type: str, websocket_manager=None
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

                    # Broadcast badge earned notification via WebSocket
                    if websocket_manager:
                        badge = await self.badge_repo.get_by_pk(check.badge_pk)
                        if badge:
                            try:
                                event_broadcaster = get_event_broadcaster(
                                    websocket_manager
                                )
                                await event_broadcaster.broadcast_badge_earned(
                                    user_id=user_id,
                                    badge_id=check.badge_pk,
                                    badge_name=badge.name,
                                    badge_description=badge.description,
                                    badge_icon=badge.image_url,
                                )
                            except Exception as e:
                                logger.warning(f"Failed to broadcast badge earned: {e}")
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
