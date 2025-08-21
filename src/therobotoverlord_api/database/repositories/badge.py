"""Badge repository for The Robot Overlord API."""

from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.badge import Badge
from therobotoverlord_api.database.models.badge import UserBadge
from therobotoverlord_api.database.models.badge import UserBadgeWithDetails
from therobotoverlord_api.database.repositories.base import BaseRepository


class BadgeRepository(BaseRepository[Badge]):
    """Repository for badge operations."""

    def __init__(self):
        super().__init__("badges")

    def _record_to_model(self, record: Record) -> Badge:
        """Convert database record to Badge model."""
        return Badge.model_validate(record)

    async def get_active_badges(self) -> list[Badge]:
        """Get all active badges."""
        return await self.find_by(is_active=True)

    async def get_by_name(self, name: str) -> Badge | None:
        """Get badge by name."""
        return await self.find_one_by(name=name)

    async def get_badges_by_type(self, badge_type: str) -> list[Badge]:
        """Get badges by type (positive/negative)."""
        return await self.find_by(badge_type=badge_type, is_active=True)


class UserBadgeRepository(BaseRepository[UserBadge]):
    """Repository for user badge operations."""

    def __init__(self):
        super().__init__("user_badges")

    def _record_to_model(self, record: Record) -> UserBadge:
        """Convert database record to UserBadge model."""
        return UserBadge.model_validate(record)

    async def get_user_badges(self, user_pk: UUID) -> list[UserBadgeWithDetails]:
        """Get all badges for a user with badge details."""
        query = """
            SELECT
                ub.pk as user_badge_pk,
                ub.user_pk,
                ub.badge_pk,
                ub.awarded_at,
                ub.awarded_for_post_pk,
                ub.awarded_for_topic_pk,
                ub.awarded_by_event,
                ub.created_at as user_badge_created_at,
                ub.updated_at as user_badge_updated_at,
                b.pk as badge_pk,
                b.name,
                b.description,
                b.image_url,
                b.badge_type,
                b.criteria_config,
                b.is_active,
                b.created_at as badge_created_at,
                b.updated_at as badge_updated_at,
                u.username
            FROM user_badges ub
            JOIN badges b ON ub.badge_pk = b.pk
            JOIN users u ON ub.user_pk = u.pk
            WHERE ub.user_pk = $1 AND b.is_active = TRUE
            ORDER BY ub.awarded_at DESC
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, user_pk)

            result = []
            for record in records:
                # Create Badge object
                badge = Badge(
                    pk=record["badge_pk"],
                    name=record["name"],
                    description=record["description"],
                    image_url=record["image_url"],
                    badge_type=record["badge_type"],
                    criteria_config=record["criteria_config"],
                    is_active=record["is_active"],
                    created_at=record["badge_created_at"],
                    updated_at=record["badge_updated_at"],
                )

                # Create UserBadgeWithDetails object
                user_badge = UserBadgeWithDetails(
                    pk=record["user_badge_pk"],
                    user_pk=record["user_pk"],
                    badge_pk=record["badge_pk"],
                    awarded_at=record["awarded_at"],
                    awarded_for_post_pk=record["awarded_for_post_pk"],
                    awarded_for_topic_pk=record["awarded_for_topic_pk"],
                    awarded_by_event=record["awarded_by_event"],
                    created_at=record["user_badge_created_at"],
                    updated_at=record["user_badge_updated_at"],
                    badge=badge,
                    username=record["username"],
                )
                result.append(user_badge)

            return result

    async def has_badge(self, user_pk: UUID, badge_pk: UUID) -> bool:
        """Check if user already has a specific badge."""
        user_badge = await self.find_one_by(user_pk=user_pk, badge_pk=badge_pk)
        return user_badge is not None

    async def award_badge(self, user_badge_data: dict) -> UserBadge:
        """Award a badge to a user."""
        return await self.create_from_dict(user_badge_data)

    async def get_user_badge_counts(self, user_pk: UUID) -> dict[str, int]:
        """Get badge counts for a user by type."""
        query = """
            SELECT
                b.badge_type,
                COUNT(*) as count
            FROM user_badges ub
            JOIN badges b ON ub.badge_pk = b.pk
            WHERE ub.user_pk = $1 AND b.is_active = TRUE
            GROUP BY b.badge_type
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, user_pk)

            counts = {"positive": 0, "negative": 0, "total": 0}
            for record in records:
                counts[record["badge_type"]] = record["count"]
                counts["total"] += record["count"]

            return counts

    async def get_recent_user_badges(
        self, user_pk: UUID, limit: int = 5
    ) -> list[UserBadgeWithDetails]:
        """Get recent badges for a user."""
        query = """
            SELECT
                ub.pk as user_badge_pk,
                ub.user_pk,
                ub.badge_pk,
                ub.awarded_at,
                ub.awarded_for_post_pk,
                ub.awarded_for_topic_pk,
                ub.awarded_by_event,
                ub.created_at as user_badge_created_at,
                ub.updated_at as user_badge_updated_at,
                b.pk as badge_pk,
                b.name,
                b.description,
                b.image_url,
                b.badge_type,
                b.criteria_config,
                b.is_active,
                b.created_at as badge_created_at,
                b.updated_at as badge_updated_at,
                u.username
            FROM user_badges ub
            JOIN badges b ON ub.badge_pk = b.pk
            JOIN users u ON ub.user_pk = u.pk
            WHERE ub.user_pk = $1 AND b.is_active = TRUE
            ORDER BY ub.awarded_at DESC
            LIMIT $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, user_pk, limit)

            result = []
            for record in records:
                badge = Badge(
                    pk=record["badge_pk"],
                    name=record["name"],
                    description=record["description"],
                    image_url=record["image_url"],
                    badge_type=record["badge_type"],
                    criteria_config=record["criteria_config"],
                    is_active=record["is_active"],
                    created_at=record["badge_created_at"],
                    updated_at=record["badge_updated_at"],
                )

                user_badge = UserBadgeWithDetails(
                    pk=record["user_badge_pk"],
                    user_pk=record["user_pk"],
                    badge_pk=record["badge_pk"],
                    awarded_at=record["awarded_at"],
                    awarded_for_post_pk=record["awarded_for_post_pk"],
                    awarded_for_topic_pk=record["awarded_for_topic_pk"],
                    awarded_by_event=record["awarded_by_event"],
                    created_at=record["user_badge_created_at"],
                    updated_at=record["user_badge_updated_at"],
                    badge=badge,
                    username=record["username"],
                )
                result.append(user_badge)

            return result

    async def get_badge_recipients(
        self, badge_pk: UUID, limit: int = 100
    ) -> list[UserBadgeWithDetails]:
        """Get users who have received a specific badge."""
        query = """
            SELECT
                ub.pk as user_badge_pk,
                ub.user_pk,
                ub.badge_pk,
                ub.awarded_at,
                ub.awarded_for_post_pk,
                ub.awarded_for_topic_pk,
                ub.awarded_by_event,
                ub.created_at as user_badge_created_at,
                ub.updated_at as user_badge_updated_at,
                b.pk as badge_pk,
                b.name,
                b.description,
                b.image_url,
                b.badge_type,
                b.criteria_config,
                b.is_active,
                b.created_at as badge_created_at,
                b.updated_at as badge_updated_at,
                u.username
            FROM user_badges ub
            JOIN badges b ON ub.badge_pk = b.pk
            JOIN users u ON ub.user_pk = u.pk
            WHERE ub.badge_pk = $1 AND b.is_active = TRUE
            ORDER BY ub.awarded_at DESC
            LIMIT $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, badge_pk, limit)

            result = []
            for record in records:
                badge = Badge(
                    pk=record["badge_pk"],
                    name=record["name"],
                    description=record["description"],
                    image_url=record["image_url"],
                    badge_type=record["badge_type"],
                    criteria_config=record["criteria_config"],
                    is_active=record["is_active"],
                    created_at=record["badge_created_at"],
                    updated_at=record["badge_updated_at"],
                )

                user_badge = UserBadgeWithDetails(
                    pk=record["user_badge_pk"],
                    user_pk=record["user_pk"],
                    badge_pk=record["badge_pk"],
                    awarded_at=record["awarded_at"],
                    awarded_for_post_pk=record["awarded_for_post_pk"],
                    awarded_for_topic_pk=record["awarded_for_topic_pk"],
                    awarded_by_event=record["awarded_by_event"],
                    created_at=record["user_badge_created_at"],
                    updated_at=record["user_badge_updated_at"],
                    badge=badge,
                    username=record["username"],
                )
                result.append(user_badge)

            return result
