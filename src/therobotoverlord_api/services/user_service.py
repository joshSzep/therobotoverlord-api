"""User service for user management operations."""

from uuid import UUID

from therobotoverlord_api.database.models.badge import UserBadge
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserProfile
from therobotoverlord_api.database.models.user import UserUpdate
from therobotoverlord_api.database.repositories.badge import BadgeRepository
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
    ):
        self.user_repo = user_repo
        self.post_repo = post_repo
        self.topic_repo = topic_repo
        self.badge_repo = badge_repo

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

    async def get_user_badges(self, user_id: UUID) -> list[UserBadge]:
        """Get user's badges."""
        return await self.badge_repo.get_user_badges(user_id)

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
    )
