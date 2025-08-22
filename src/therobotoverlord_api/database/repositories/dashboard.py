"""Dashboard repository for The Robot Overlord API."""

from datetime import datetime

from asyncpg import Record

from therobotoverlord_api.database.models.dashboard_snapshot import DashboardSnapshot
from therobotoverlord_api.database.models.dashboard_snapshot import (
    DashboardSnapshotCreate,
)
from therobotoverlord_api.database.models.dashboard_snapshot import (
    DashboardSnapshotType,
)
from therobotoverlord_api.database.repositories.base import BaseRepository


class DashboardRepository(BaseRepository[DashboardSnapshot]):
    """Repository for dashboard snapshot storage and retrieval."""

    def __init__(self):
        super().__init__("dashboard_snapshots")

    def _record_to_model(self, record: Record) -> DashboardSnapshot:
        """Convert database record to DashboardSnapshot model."""
        return DashboardSnapshot.model_validate(dict(record))

    async def create_snapshot(
        self, snapshot: DashboardSnapshotCreate
    ) -> DashboardSnapshot:
        """Store dashboard metrics snapshot."""
        data = snapshot.model_dump()
        return await self.create_from_dict(data)

    async def get_snapshots_by_period(
        self,
        snapshot_type: DashboardSnapshotType,
        start_date: datetime,
        end_date: datetime,
    ) -> list[DashboardSnapshot]:
        """Get historical snapshots for trend analysis."""
        query = """
            SELECT * FROM dashboard_snapshots
            WHERE snapshot_type = $1
            AND period_start >= $2
            AND period_end <= $3
            ORDER BY period_start DESC
        """

        from therobotoverlord_api.database.connection import get_db_connection

        async with get_db_connection() as connection:
            records = await connection.fetch(
                query, snapshot_type.value, start_date, end_date
            )
            return [self._record_to_model(record) for record in records]

    async def get_latest_snapshot(
        self,
        snapshot_type: DashboardSnapshotType,
    ) -> DashboardSnapshot | None:
        """Get the most recent snapshot of a given type."""
        query = """
            SELECT * FROM dashboard_snapshots
            WHERE snapshot_type = $1
            ORDER BY generated_at DESC
            LIMIT 1
        """

        from therobotoverlord_api.database.connection import get_db_connection

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, snapshot_type.value)
            return self._record_to_model(record) if record else None

    async def cleanup_old_snapshots(
        self,
        snapshot_type: DashboardSnapshotType,
        keep_count: int = 100,
    ) -> int:
        """Remove old snapshots, keeping only the most recent ones."""
        query = """
            DELETE FROM dashboard_snapshots
            WHERE pk IN (
                SELECT pk FROM dashboard_snapshots
                WHERE snapshot_type = $1
                ORDER BY generated_at DESC
                OFFSET $2
            )
        """

        from therobotoverlord_api.database.connection import get_db_connection

        async with get_db_connection() as connection:
            result = await connection.execute(query, snapshot_type.value, keep_count)
            # Extract number from "DELETE n" result
            return int(result.split()[-1]) if result.startswith("DELETE") else 0
