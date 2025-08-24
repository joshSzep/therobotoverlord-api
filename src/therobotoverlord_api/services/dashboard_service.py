"""Dashboard service for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from typing import Any
from uuid import UUID

from therobotoverlord_api.database.models.admin_action import AdminAction
from therobotoverlord_api.database.models.admin_action import AdminActionCreate
from therobotoverlord_api.database.models.admin_action import AdminActionType
from therobotoverlord_api.database.models.dashboard_snapshot import (
    ContentActivitySummary,
)
from therobotoverlord_api.database.models.dashboard_snapshot import DashboardOverview
from therobotoverlord_api.database.models.dashboard_snapshot import (
    ModerationActivitySummary,
)
from therobotoverlord_api.database.models.dashboard_snapshot import RecentActivity
from therobotoverlord_api.database.models.dashboard_snapshot import SystemHealthSummary
from therobotoverlord_api.database.models.dashboard_snapshot import UserActivitySummary
from therobotoverlord_api.database.models.dashboard_snapshot import UserSummary
from therobotoverlord_api.database.models.system_announcement import AnnouncementCreate
from therobotoverlord_api.database.models.system_announcement import SystemAnnouncement
from therobotoverlord_api.database.repositories.admin_action import (
    AdminActionRepository,
)
from therobotoverlord_api.database.repositories.system_announcement import (
    SystemAnnouncementRepository,
)
from therobotoverlord_api.services.appeal_service import AppealService
from therobotoverlord_api.services.flag_service import FlagService
from therobotoverlord_api.services.leaderboard_service import LeaderboardService
from therobotoverlord_api.services.loyalty_score_service import LoyaltyScoreService
from therobotoverlord_api.services.queue_service import QueueService
from therobotoverlord_api.services.sanction_service import SanctionService
from therobotoverlord_api.services.user_service import UserService


class DashboardService:
    """Service for aggregating dashboard data from existing systems."""

    def __init__(self):
        # Initialize repositories first
        from therobotoverlord_api.database.repositories.badge import BadgeRepository
        from therobotoverlord_api.database.repositories.badge import UserBadgeRepository
        from therobotoverlord_api.database.repositories.post import PostRepository
        from therobotoverlord_api.database.repositories.sanction import (
            SanctionRepository,
        )
        from therobotoverlord_api.database.repositories.topic import TopicRepository
        from therobotoverlord_api.database.repositories.user import UserRepository

        user_repo = UserRepository()
        post_repo = PostRepository()
        topic_repo = TopicRepository()
        badge_repo = BadgeRepository()
        user_badge_repo = UserBadgeRepository()
        sanction_repo = SanctionRepository()

        # Use existing services with required dependencies
        self.user_service = UserService(
            user_repo, post_repo, topic_repo, badge_repo, user_badge_repo
        )
        self.sanction_service = SanctionService(sanction_repo, user_repo)
        self.flag_service = FlagService()
        self.appeal_service = AppealService()
        self.queue_service = QueueService()
        self.loyalty_service = LoyaltyScoreService()
        self.leaderboard_service = LeaderboardService()

        # New components for dashboard-specific functionality
        self.admin_action_repository = AdminActionRepository()
        self.announcement_repository = SystemAnnouncementRepository()

    async def get_dashboard_overview(self, period: str = "24h") -> DashboardOverview:
        """Aggregate dashboard data from all existing systems."""

        # Aggregate user metrics from existing user/loyalty systems
        user_metrics = await self._aggregate_user_metrics(period)

        # Aggregate content metrics from existing content systems
        content_metrics = await self._aggregate_content_metrics(period)

        # Aggregate moderation metrics from existing moderation systems
        moderation_metrics = await self._aggregate_moderation_metrics(period)

        # Aggregate system health from existing health endpoints
        system_health = await self._aggregate_system_health()

        # Get recent activity from audit log
        recent_activity = await self._get_recent_activity()

        return DashboardOverview(
            user_metrics=user_metrics,
            content_metrics=content_metrics,
            moderation_metrics=moderation_metrics,
            system_health=system_health,
            recent_activity=recent_activity,
            generated_at=datetime.now(UTC),
        )

    async def _aggregate_user_metrics(self, period: str) -> UserActivitySummary:
        """Aggregate user metrics from existing user and loyalty systems."""
        # Get basic user counts
        total_users = await self.user_service.get_total_user_count()

        # Get active user counts (simplified - would need time-based queries)
        active_users_24h = await self.user_service.get_active_user_count("24h")
        active_users_7d = await self.user_service.get_active_user_count("7d")

        # Get registration counts
        new_registrations_24h = await self.user_service.get_new_registrations_count(
            "24h"
        )

        # Get banned/sanctioned user counts
        banned_users = await self.user_service.get_banned_user_count()
        sanctioned_users = await self.sanction_service.get_sanctioned_user_count()

        # Get top contributors from leaderboard
        top_contributors_data = await self.leaderboard_service.get_top_contributors(
            limit=5
        )
        top_contributors = [
            UserSummary(
                pk=user.pk,
                username=user.username,
                role=user.role.value,
                loyalty_score=user.loyalty_score,
            )
            for user in top_contributors_data
        ]

        return UserActivitySummary(
            total_users=total_users,
            active_users_24h=active_users_24h,
            active_users_7d=active_users_7d,
            new_registrations_24h=new_registrations_24h,
            banned_users=banned_users,
            sanctioned_users=sanctioned_users,
            top_contributors=top_contributors,
        )

    async def _aggregate_content_metrics(self, period: str) -> ContentActivitySummary:
        """Aggregate content metrics from existing content systems."""
        # Get queue statistics for content metrics
        queue_stats = await self.queue_service.get_queue_statistics()

        # Get flag statistics
        flag_stats = await self.flag_service.get_system_flag_statistics()

        # Get appeal statistics
        appeal_stats = await self.appeal_service.get_system_appeal_statistics()

        return ContentActivitySummary(
            posts_created_24h=queue_stats.get("posts_submitted_24h", 0),
            posts_approved_24h=queue_stats.get("posts_approved_24h", 0),
            posts_rejected_24h=queue_stats.get("posts_rejected_24h", 0),
            topics_created_24h=queue_stats.get("topics_submitted_24h", 0),
            flags_submitted_24h=flag_stats.get("flags_submitted_24h", 0),
            appeals_submitted_24h=appeal_stats.get("appeals_submitted_24h", 0),
            moderation_queue_size=queue_stats.get("pending_items", 0),
        )

    async def _aggregate_moderation_metrics(
        self, period: str
    ) -> ModerationActivitySummary:
        """Aggregate moderation metrics from existing moderation systems."""
        # Get pending flags and appeals
        flags_pending = await self.flag_service.get_pending_flags_count()
        appeals_pending = await self.appeal_service.get_pending_appeals_count()

        # Get sanction statistics
        sanctions_applied_24h = await self.sanction_service.get_sanctions_applied_count(
            "24h"
        )

        # Get moderator action count from admin actions
        moderator_actions_24h = await self._get_moderator_actions_count("24h")

        # Get queue processing times
        queue_processing_times = await self.queue_service.get_processing_times()

        return ModerationActivitySummary(
            flags_pending=flags_pending,
            appeals_pending=appeals_pending,
            sanctions_applied_24h=sanctions_applied_24h,
            moderator_actions_24h=moderator_actions_24h,
            queue_processing_times=queue_processing_times,
        )

    async def _aggregate_system_health(self) -> SystemHealthSummary:
        """Aggregate system health from existing health checks."""
        # Get database health
        from therobotoverlord_api.database.connection import db

        database_healthy = await db.health_check()

        # Get queue health
        queue_health = await self.queue_service.get_health_status()

        # Simplified health aggregation
        overall_status = (
            "healthy"
            if database_healthy and queue_health.get("healthy", False)
            else "degraded"
        )

        return SystemHealthSummary(
            overall_status=overall_status,
            database_healthy=database_healthy,
            redis_healthy=True,  # Would need Redis health check
            queue_healthy=queue_health.get("healthy", False),
            worker_status=queue_health.get("workers", {}),
            response_time_avg=queue_health.get("avg_response_time", 0.0),
        )

    async def _get_recent_activity(self, limit: int = 10) -> list[RecentActivity]:
        """Get recent administrative activity from audit log."""
        recent_actions = await self.admin_action_repository.get_recent_actions(
            limit=limit
        )

        return [
            RecentActivity(
                activity_type=action.action_type.value,
                description=action.description,
                user_id=action.target_pk if action.target_type == "user" else None,
                moderator_id=action.admin_pk,
                timestamp=action.created_at,
            )
            for action in recent_actions
        ]

    async def _get_moderator_actions_count(self, period: str) -> int:
        """Get count of moderator actions in the given period."""
        # Simplified - would need time-based filtering
        return await self.admin_action_repository.get_actions_count()

    async def log_admin_action(
        self,
        admin_pk: UUID,
        action_type: AdminActionType,
        description: str,
        target_type: str | None = None,
        target_pk: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AdminAction:
        """Log administrative action for audit trail."""

        action = AdminActionCreate(
            admin_pk=admin_pk,
            action_type=action_type,
            target_type=target_type,
            target_pk=target_pk,
            description=description,
            metadata=metadata or {},
            ip_address=ip_address,
        )

        return await self.admin_action_repository.create_action(action)

    async def create_announcement(
        self, announcement: AnnouncementCreate, created_by_pk: UUID
    ) -> SystemAnnouncement:
        """Create system announcement."""
        return await self.announcement_repository.create_announcement(
            announcement, created_by_pk
        )

    async def get_announcements(
        self,
        active_only: bool = True,  # noqa: FBT001, FBT002
    ) -> list[SystemAnnouncement]:
        """Get system announcements."""
        if active_only:
            return await self.announcement_repository.get_active_announcements()
        return await self.announcement_repository.get_all()

    async def get_audit_log(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """Get admin action audit log."""
        actions = await self.admin_action_repository.get_recent_actions(
            limit=limit, offset=offset
        )
        total_count = await self.admin_action_repository.get_actions_count()

        return {
            "actions": actions,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }
