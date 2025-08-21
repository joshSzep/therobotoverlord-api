"""Sanction service for The Robot Overlord API."""

import logging

from uuid import UUID

from therobotoverlord_api.database.models.sanction import Sanction
from therobotoverlord_api.database.models.sanction import SanctionCreate
from therobotoverlord_api.database.models.sanction import SanctionType
from therobotoverlord_api.database.models.sanction import SanctionUpdate
from therobotoverlord_api.database.models.sanction import SanctionWithDetails
from therobotoverlord_api.database.repositories.sanction import SanctionRepository
from therobotoverlord_api.database.repositories.sanction import get_sanction_repository
from therobotoverlord_api.database.repositories.user import UserRepository
from therobotoverlord_api.database.repositories.user import get_user_repository

logger = logging.getLogger(__name__)


class SanctionService:
    """Service for managing user sanctions."""

    def __init__(
        self,
        sanction_repository: SanctionRepository,
        user_repository: UserRepository,
    ):
        self.sanction_repository = sanction_repository
        self.user_repository = user_repository

    async def apply_sanction(
        self,
        sanction_data: SanctionCreate,
        applied_by_pk: UUID,
    ) -> Sanction | None:
        """Apply a sanction to a user."""
        # Validate that the user exists
        user = await self.user_repository.get_by_pk(sanction_data.user_pk)
        if not user:
            raise ValueError("User not found")

        # Validate that the moderator exists
        moderator = await self.user_repository.get_by_pk(applied_by_pk)
        if not moderator:
            raise ValueError("Moderator not found")

        # Create the sanction
        sanction = await self.sanction_repository.create_sanction(
            sanction_data,
            applied_by_pk,
        )

        # Update user sanction status if needed
        await self._update_user_sanction_status(sanction_data.user_pk)

        if sanction is None:
            logger.error(
                f"Failed to create sanction for user {sanction_data.user_pk} "
                f"by {applied_by_pk}. Reason: {sanction_data.reason}"
            )
            return None

        logger.info(
            f"Sanction {sanction.type} applied to user {sanction_data.user_pk} "
            f"by {applied_by_pk}. Reason: {sanction_data.reason}"
        )

        return sanction

    async def get_user_sanctions(
        self,
        user_pk: UUID,
        *,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Sanction]:
        """Get sanctions for a specific user."""
        return await self.sanction_repository.get_sanctions_by_user(
            user_pk,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )

    async def get_all_sanctions(
        self,
        sanction_type: SanctionType | None = None,
        *,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SanctionWithDetails]:
        """Get all sanctions with user details for admin view."""
        return await self.sanction_repository.get_all_sanctions(
            sanction_type=sanction_type,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )

    async def update_sanction(
        self,
        sanction_pk: UUID,
        sanction_data: SanctionUpdate,
    ) -> Sanction | None:
        """Update a sanction."""
        # Get the current sanction to check user_pk
        current_sanction = await self.sanction_repository.get_by_pk(sanction_pk)
        if not current_sanction:
            return None

        # Update the sanction
        updated_sanction = await self.sanction_repository.update_sanction(
            sanction_pk,
            sanction_data,
        )

        if updated_sanction:
            # Update user sanction status
            await self._update_user_sanction_status(current_sanction.user_pk)

            logger.info(f"Sanction {sanction_pk} updated")

        return updated_sanction

    async def remove_sanction(self, sanction_pk: UUID) -> bool:
        """Remove (deactivate) a sanction."""
        # Get the current sanction to check user_pk
        current_sanction = await self.sanction_repository.get_by_pk(sanction_pk)
        if not current_sanction:
            return False

        success = await self.sanction_repository.deactivate_sanction(sanction_pk)

        if success:
            # Update user sanction status
            await self._update_user_sanction_status(current_sanction.user_pk)

            logger.info(f"Sanction {sanction_pk} removed")

        return success

    async def get_active_user_sanctions(self, user_pk: UUID) -> list[Sanction]:
        """Get all active sanctions for a user."""
        return await self.sanction_repository.get_active_sanctions_by_user(user_pk)

    async def is_user_banned(self, user_pk: UUID) -> bool:
        """Check if a user has an active ban."""
        active_sanctions = await self.get_active_user_sanctions(user_pk)

        for sanction in active_sanctions:
            if sanction.type in [
                SanctionType.TEMPORARY_BAN,
                SanctionType.PERMANENT_BAN,
            ]:
                return True

        return False

    async def can_user_post(self, user_pk: UUID) -> bool:
        """Check if a user can create posts."""
        active_sanctions = await self.get_active_user_sanctions(user_pk)

        for sanction in active_sanctions:
            if sanction.type in [
                SanctionType.TEMPORARY_BAN,
                SanctionType.PERMANENT_BAN,
                SanctionType.POST_RESTRICTION,
            ]:
                return False

        return True

    async def can_user_create_topics(self, user_pk: UUID) -> bool:
        """Check if a user can create topics."""
        active_sanctions = await self.get_active_user_sanctions(user_pk)

        for sanction in active_sanctions:
            if sanction.type in [
                SanctionType.TEMPORARY_BAN,
                SanctionType.PERMANENT_BAN,
                SanctionType.POST_RESTRICTION,
                SanctionType.TOPIC_RESTRICTION,
            ]:
                return False

        return True

    async def expire_sanctions(self) -> int:
        """Expire sanctions that have passed their expiration date."""
        expired_count = await self.sanction_repository.expire_sanctions()

        if expired_count > 0:
            logger.info(f"Expired {expired_count} sanctions")

        return expired_count

    async def get_sanction_summary(self, user_pk: UUID) -> dict:
        """Get a summary of sanctions for a user."""
        active_sanctions = await self.get_active_user_sanctions(user_pk)
        total_sanctions = await self.sanction_repository.get_sanction_count_by_user(
            user_pk
        )

        sanction_counts = {}
        for sanction_type in SanctionType:
            count = await self.sanction_repository.get_sanction_count_by_user(
                user_pk,
                sanction_type,
            )
            sanction_counts[sanction_type.value] = count

        return {
            "user_pk": user_pk,
            "active_sanctions_count": len(active_sanctions),
            "total_sanctions_count": total_sanctions,
            "sanction_counts_by_type": sanction_counts,
            "is_banned": await self.is_user_banned(user_pk),
            "can_post": await self.can_user_post(user_pk),
            "can_create_topics": await self.can_user_create_topics(user_pk),
            "active_sanctions": active_sanctions,
        }

    async def _update_user_sanction_status(self, user_pk: UUID) -> None:
        """Update the user's sanction status based on active sanctions."""
        is_banned = await self.is_user_banned(user_pk)
        active_sanctions = await self.get_active_user_sanctions(user_pk)

        # Update user's is_sanctioned and is_banned flags
        has_active_sanctions = len(active_sanctions) > 0

        # Use the user repository to update the user's status
        # This assumes the user repository has an update method
        try:
            from therobotoverlord_api.database.models.user import UserUpdate

            user_update = UserUpdate(
                is_banned=is_banned,
                is_sanctioned=has_active_sanctions,
            )

            await self.user_repository.update_user(user_pk, user_update)
        except Exception as e:
            logger.error(f"Failed to update user sanction status: {e}")


def get_sanction_service() -> SanctionService:
    """Get sanction service instance."""
    return SanctionService(
        sanction_repository=get_sanction_repository(),
        user_repository=get_user_repository(),
    )
