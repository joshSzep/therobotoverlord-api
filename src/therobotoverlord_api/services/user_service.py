"""User service for user management operations."""

from uuid import UUID

from therobotoverlord_api.database.models.badge import UserBadgeSummary
from therobotoverlord_api.database.models.badge import UserBadgeWithDetails
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserProfile
from therobotoverlord_api.database.models.user import UserUpdate
from therobotoverlord_api.database.repositories.badge import BadgeRepository
from therobotoverlord_api.database.repositories.badge import UserBadgeRepository
from therobotoverlord_api.database.repositories.post import PostRepository
from therobotoverlord_api.database.repositories.topic import TopicRepository
from therobotoverlord_api.database.repositories.user import UserRepository


class UserService:
    """Service for user management operations."""

    def __init__(
        self,
        user_repo: UserRepository,
        post_repo: PostRepository,
        topic_repo: TopicRepository,
        badge_repo: BadgeRepository,
        user_badge_repo: UserBadgeRepository,
    ):
        self.user_repo = user_repo
        self.post_repo = post_repo
        self.topic_repo = topic_repo
        self.badge_repo = badge_repo
        self.user_badge_repo = user_badge_repo

    async def get_user_profile(self, user_id: UUID) -> UserProfile | None:
        """Get public user profile."""
        user = await self.user_repo.get_by_pk(user_id)
        if not user:
            return None

        return UserProfile(
            pk=user.pk,
            username=user.username,
            loyalty_score=user.loyalty_score,
            role=user.role,
            created_at=user.created_at,
        )

    async def get_user_graveyard(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Post]:
        """Get user's rejected posts."""
        # Use the existing graveyard method that returns PostSummary
        post_summaries = await self.post_repo.get_graveyard_by_author(
            user_id, limit, offset
        )
        # Convert PostSummary to Post objects for the response
        posts = []
        for summary in post_summaries:
            post = await self.post_repo.get_by_pk(summary.pk)
            if post:
                posts.append(post)
        return posts

    async def get_user_registry(
        self,
        limit: int = 50,
        offset: int = 0,
        role_filter: UserRole | None = None,
    ) -> list[UserProfile]:
        """Get public citizen registry."""
        if role_filter:
            users = await self.user_repo.get_users_by_role(role_filter.value)
            # Apply pagination manually for filtered results
            paginated_users = users[offset : offset + limit]
        else:
            # Get all users with pagination
            users = await self.user_repo.get_all(limit=limit, offset=offset)
            paginated_users = users

        return [
            UserProfile(
                pk=user.pk,
                username=user.username,
                loyalty_score=user.loyalty_score,
                role=user.role,
                created_at=user.created_at,
            )
            for user in paginated_users
        ]

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> User | None:
        """Update user profile."""
        # Validate username uniqueness if being updated
        if user_data.username:
            existing_user = await self.user_repo.get_by_username(user_data.username)
            if existing_user and existing_user.pk != user_id:
                raise ValueError("Username already taken")

        return await self.user_repo.update_user(user_id, user_data)

    async def get_user_badges(self, user_id: UUID) -> list[UserBadgeWithDetails]:
        """Get user's badges with details."""
        return await self.user_badge_repo.get_user_badges(user_id)

    async def get_user_badge_summary(self, user_id: UUID) -> UserBadgeSummary | None:
        """Get user's badge summary for profile display."""
        user = await self.user_repo.get_by_pk(user_id)
        if not user:
            return None

        badges = await self.user_badge_repo.get_user_badges(user_id)
        counts = await self.user_badge_repo.get_user_badge_counts(user_id)
        recent_badges = await self.user_badge_repo.get_recent_user_badges(user_id, 3)

        return UserBadgeSummary(
            user_pk=user_id,
            username=user.username,
            total_badges=counts["total"],
            positive_badges=counts["positive"],
            negative_badges=counts["negative"],
            recent_badges=recent_badges,
        )

    async def get_leaderboard(
        self, limit: int = 50, offset: int = 0, badge_type: str | None = None
    ) -> list[dict]:
        """Get user leaderboard based on badges and loyalty scores."""
        # Build query based on badge type filter
        if badge_type == "positive":
            badge_filter = "AND b.badge_type = 'positive'"
        elif badge_type == "negative":
            badge_filter = "AND b.badge_type = 'negative'"
        else:
            badge_filter = ""

        query = f"""
            SELECT
                u.pk,
                u.username,
                u.loyalty_score,
                u.role,
                u.created_at,
                COUNT(CASE WHEN b.badge_type = 'positive' THEN 1 END) as positive_badges,
                COUNT(CASE WHEN b.badge_type = 'negative' THEN 1 END) as negative_badges,
                COUNT(ub.pk) as total_badges,
                -- Calculate leaderboard score: loyalty_score + (positive_badges * 10) - (negative_badges * 5)
                (u.loyalty_score +
                 COUNT(CASE WHEN b.badge_type = 'positive' THEN 1 END) * 10 -
                 COUNT(CASE WHEN b.badge_type = 'negative' THEN 1 END) * 5) as leaderboard_score
            FROM users u
            LEFT JOIN user_badges ub ON u.pk = ub.user_pk
            LEFT JOIN badges b ON ub.badge_pk = b.pk {badge_filter}
            WHERE u.is_banned = FALSE
            GROUP BY u.pk, u.username, u.loyalty_score, u.role, u.created_at
            ORDER BY leaderboard_score DESC, u.loyalty_score DESC, u.created_at ASC
            LIMIT $1 OFFSET $2
        """

        from therobotoverlord_api.database.connection import get_db_connection

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)

            leaderboard = []
            for i, record in enumerate(records):
                leaderboard.append(
                    {
                        "rank": offset + i + 1,
                        "user_id": record["pk"],
                        "username": record["username"],
                        "loyalty_score": record["loyalty_score"],
                        "role": record["role"],
                        "positive_badges": record["positive_badges"],
                        "negative_badges": record["negative_badges"],
                        "total_badges": record["total_badges"],
                        "leaderboard_score": record["leaderboard_score"],
                        "created_at": record["created_at"],
                    }
                )

            return leaderboard

    async def get_badge_leaderboard(
        self, badge_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        """Get leaderboard for users who have earned a specific badge."""
        query = """
            SELECT
                u.pk,
                u.username,
                u.loyalty_score,
                u.role,
                ub.awarded_at,
                b.name as badge_name,
                b.description as badge_description
            FROM user_badges ub
            JOIN users u ON ub.user_pk = u.pk
            JOIN badges b ON ub.badge_pk = b.pk
            WHERE ub.badge_pk = $1 AND u.is_banned = FALSE
            ORDER BY ub.awarded_at ASC
            LIMIT $2 OFFSET $3
        """

        from therobotoverlord_api.database.connection import get_db_connection

        async with get_db_connection() as connection:
            records = await connection.fetch(query, badge_id, limit, offset)

            leaderboard = []
            for i, record in enumerate(records):
                leaderboard.append(
                    {
                        "rank": offset + i + 1,
                        "user_id": record["pk"],
                        "username": record["username"],
                        "loyalty_score": record["loyalty_score"],
                        "role": record["role"],
                        "awarded_at": record["awarded_at"],
                        "badge_name": record["badge_name"],
                        "badge_description": record["badge_description"],
                    }
                )

            return leaderboard

    async def get_user_activity(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> dict:
        """Get user's activity feed."""
        # Get user's recent posts and topics
        user_posts = await self.post_repo.get_by_author(
            user_id, None, limit // 2, offset // 2
        )
        user_topics = await self.topic_repo.get_by_author(
            user_id, limit // 2, offset // 2
        )

        return {
            "posts": user_posts,
            "topics": user_topics,
            "total_posts": len(user_posts),
            "total_topics": len(user_topics),
        }

    async def delete_user_account(self, user_id: UUID) -> bool:
        """Delete user account (GDPR compliance)."""
        user = await self.user_repo.get_by_pk(user_id)
        if not user:
            return False

        # In a real implementation, this would:
        # 1. Anonymize or delete user's posts/topics
        # 2. Remove personal data while preserving content structure
        # 3. Update foreign key references
        # 4. Log the deletion for audit purposes

        # For now, we'll just mark the user as deleted by updating their data
        anonymized_data = UserUpdate(
            username=f"deleted_user_{user_id}",
            email_verified=False,
            is_banned=True,
        )

        result = await self.user_repo.update_user(user_id, anonymized_data)
        return result is not None


def get_user_service() -> UserService:
    """Dependency injection for UserService."""
    return UserService(
        user_repo=UserRepository(),
        post_repo=PostRepository(),
        topic_repo=TopicRepository(),
        badge_repo=BadgeRepository(),
        user_badge_repo=UserBadgeRepository(),
    )
