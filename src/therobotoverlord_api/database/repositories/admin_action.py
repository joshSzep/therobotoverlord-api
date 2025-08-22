"""Admin action repository for The Robot Overlord API."""

from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.models.admin_action import AdminAction
from therobotoverlord_api.database.models.admin_action import AdminActionCreate
from therobotoverlord_api.database.repositories.base import BaseRepository


class AdminActionRepository(BaseRepository[AdminAction]):
    """Repository for admin action audit trail."""

    def __init__(self):
        super().__init__("admin_actions")

    def _record_to_model(self, record: Record) -> AdminAction:
        """Convert database record to AdminAction model."""
        return AdminAction.model_validate(dict(record))

    async def create_action(self, action: AdminActionCreate) -> AdminAction:
        """Log administrative action."""
        data = action.model_dump()
        return await self.create_from_dict(data)

    async def get_actions_by_admin(
        self,
        admin_pk: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AdminAction]:
        """Get actions performed by specific admin."""
        return await self.find_by(admin_pk=admin_pk)

    async def get_recent_actions(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AdminAction]:
        """Get recent administrative actions."""
        return await self.get_all(limit=limit, offset=offset)

    async def get_actions_count(self) -> int:
        """Get total count of admin actions."""
        return await self.count()

    async def get_actions_by_type(
        self,
        action_type: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AdminAction]:
        """Get actions by type."""
        return await self.find_by(action_type=action_type)

    async def get_actions_for_target(
        self,
        target_pk: UUID,
        target_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AdminAction]:
        """Get actions performed on a specific target."""
        filters: dict[str, UUID | str] = {"target_pk": target_pk}
        if target_type:
            filters["target_type"] = target_type
        return await self.find_by(**filters)
