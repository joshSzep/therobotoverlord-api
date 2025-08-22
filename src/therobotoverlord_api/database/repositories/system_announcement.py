"""System announcement repository for The Robot Overlord API."""

from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.models.system_announcement import AnnouncementCreate
from therobotoverlord_api.database.models.system_announcement import SystemAnnouncement
from therobotoverlord_api.database.repositories.base import BaseRepository


class SystemAnnouncementRepository(BaseRepository[SystemAnnouncement]):
    """Repository for system announcements."""

    def __init__(self):
        super().__init__("system_announcements")

    def _record_to_model(self, record: Record) -> SystemAnnouncement:
        """Convert database record to SystemAnnouncement model."""
        return SystemAnnouncement.model_validate(dict(record))

    async def create_announcement(
        self,
        announcement: AnnouncementCreate,
        created_by_pk: UUID,
    ) -> SystemAnnouncement:
        """Create system announcement."""
        data = announcement.model_dump()
        data["created_by_pk"] = created_by_pk
        data["is_active"] = True

        # Create the announcement
        new_announcement = await self.create_from_dict(data)

        # Broadcast the announcement via WebSocket
        if new_announcement:
            from therobotoverlord_api.websocket.events import get_event_broadcaster
            from therobotoverlord_api.websocket.manager import websocket_manager

            event_broadcaster = get_event_broadcaster(websocket_manager)
            await event_broadcaster.broadcast_system_announcement(
                title=new_announcement.title,
                message=new_announcement.content,
                announcement_type=new_announcement.announcement_type.value,
                expires_at=new_announcement.expires_at,
            )

        return new_announcement

    async def get_active_announcements(self) -> list[SystemAnnouncement]:
        """Get currently active announcements."""
        query = """
            SELECT * FROM system_announcements
            WHERE is_active = true
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
        """

        from therobotoverlord_api.database.connection import get_db_connection

        async with get_db_connection() as connection:
            records = await connection.fetch(query)
            return [self._record_to_model(record) for record in records]

    async def get_announcements_by_creator(
        self,
        created_by_pk: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SystemAnnouncement]:
        """Get announcements created by specific admin."""
        return await self.find_by(created_by_pk=created_by_pk)

    async def deactivate_announcement(self, pk: UUID) -> SystemAnnouncement | None:
        """Deactivate an announcement."""
        return await self.update_from_dict(pk, {"is_active": False})

    async def expire_old_announcements(self) -> int:
        """Expire announcements that have passed their expiration date."""
        query = """
            UPDATE system_announcements
            SET is_active = false, updated_at = NOW()
            WHERE is_active = true
            AND expires_at IS NOT NULL
            AND expires_at <= NOW()
        """

        from therobotoverlord_api.database.connection import get_db_connection

        async with get_db_connection() as connection:
            result = await connection.execute(query)
            # Extract number from "UPDATE n" result
            return int(result.split()[-1]) if result.startswith("UPDATE") else 0

    async def get_announcements_for_role(
        self,
        role: str,
        active_only: bool = True,  # noqa: FBT001, FBT002
    ) -> list[SystemAnnouncement]:
        """Get announcements targeted at a specific role."""
        query = """
            SELECT * FROM system_announcements
            WHERE (target_roles = '[]' OR $1 = ANY(target_roles))
        """

        if active_only:
            query += (
                " AND is_active = true AND (expires_at IS NULL OR expires_at > NOW())"
            )

        query += " ORDER BY created_at DESC"

        from therobotoverlord_api.database.connection import get_db_connection

        async with get_db_connection() as connection:
            records = await connection.fetch(query, role)
            return [self._record_to_model(record) for record in records]
