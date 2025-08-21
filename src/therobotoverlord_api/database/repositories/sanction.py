"""Sanction repository for The Robot Overlord API."""

from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.sanction import Sanction
from therobotoverlord_api.database.models.sanction import SanctionCreate
from therobotoverlord_api.database.models.sanction import SanctionType
from therobotoverlord_api.database.models.sanction import SanctionUpdate
from therobotoverlord_api.database.models.sanction import SanctionWithDetails
from therobotoverlord_api.database.repositories.base import BaseRepository


class SanctionRepository(BaseRepository[Sanction]):
    """Repository for sanction database operations."""

    def __init__(self):
        super().__init__("sanctions")

    def _record_to_model(self, record: Record) -> Sanction:
        """Convert database record to Sanction model."""
        return Sanction.model_validate(dict(record))

    def _record_to_sanction_with_details(self, record: Record) -> SanctionWithDetails:
        """Convert database record to SanctionWithDetails model."""
        return SanctionWithDetails.model_validate(dict(record))

    async def create_sanction(
        self,
        sanction_data: SanctionCreate,
        applied_by_pk: UUID,
    ) -> Sanction:
        """Create a new sanction."""
        query = """
            INSERT INTO sanctions (user_pk, type, applied_by_pk, expires_at, reason)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(
                query,
                sanction_data.user_pk,
                sanction_data.type.value,
                applied_by_pk,
                sanction_data.expires_at,
                sanction_data.reason,
            )
            return self._record_to_model(record)

    async def get_sanctions_by_user(
        self,
        user_pk: UUID,
        *,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Sanction]:
        """Get sanctions for a specific user."""
        where_clause = "WHERE user_pk = $1"
        params = [user_pk]

        if active_only:
            where_clause += " AND is_active = TRUE"

        query = f"""
            SELECT * FROM sanctions
            {where_clause}
            ORDER BY applied_at DESC
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(
                query,
                *params,
                limit,
                offset,
            )
            return [self._record_to_model(record) for record in records]

    async def get_all_sanctions(
        self,
        sanction_type: SanctionType | None = None,
        *,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SanctionWithDetails]:
        """Get all sanctions with user details for admin view."""
        where_conditions = []
        params = []
        param_count = 0

        if sanction_type:
            param_count += 1
            where_conditions.append(f"s.type = ${param_count}")
            params.append(sanction_type.value)

        if active_only:
            param_count += 1
            where_conditions.append(f"s.is_active = ${param_count}")
            params.append(True)

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        query = f"""
            SELECT 
                s.*,
                u.username,
                applied_by.username as applied_by_username
            FROM sanctions s
            JOIN users u ON s.user_pk = u.pk
            JOIN users applied_by ON s.applied_by_pk = applied_by.pk
            {where_clause}
            ORDER BY s.applied_at DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(
                query,
                *params,
                limit,
                offset,
            )
            return [self._record_to_sanction_with_details(record) for record in records]

    async def update_sanction(
        self,
        sanction_pk: UUID,
        sanction_data: SanctionUpdate,
    ) -> Sanction | None:
        """Update a sanction."""
        set_clauses = []
        params = []
        param_count = 0

        if sanction_data.is_active is not None:
            param_count += 1
            set_clauses.append(f"is_active = ${param_count}")
            params.append(sanction_data.is_active)

        if sanction_data.reason is not None:
            param_count += 1
            set_clauses.append(f"reason = ${param_count}")
            params.append(sanction_data.reason)

        if sanction_data.expires_at is not None:
            param_count += 1
            set_clauses.append(f"expires_at = ${param_count}")
            params.append(sanction_data.expires_at)

        if not set_clauses:
            # No updates to make
            return await self.get_by_pk(sanction_pk)

        query = f"""
            UPDATE sanctions
            SET {', '.join(set_clauses)}
            WHERE pk = ${param_count + 1}
            RETURNING *
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(
                query,
                *params,
                sanction_pk,
            )
            return self._record_to_model(record) if record else None

    async def deactivate_sanction(self, sanction_pk: UUID) -> bool:
        """Deactivate a sanction."""
        query = """
            UPDATE sanctions
            SET is_active = FALSE
            WHERE pk = $1
            RETURNING pk
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, sanction_pk)
            return record is not None

    async def get_active_sanctions_by_user(self, user_pk: UUID) -> list[Sanction]:
        """Get all active sanctions for a user."""
        query = """
            SELECT * FROM sanctions
            WHERE user_pk = $1
            AND is_active = TRUE
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY applied_at DESC
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, user_pk)
            return [self._record_to_model(record) for record in records]

    async def expire_sanctions(self) -> int:
        """Expire sanctions that have passed their expiration date."""
        query = """
            UPDATE sanctions
            SET is_active = FALSE
            WHERE is_active = TRUE
            AND expires_at IS NOT NULL
            AND expires_at <= NOW()
            RETURNING pk
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query)
            return len(records)

    async def get_sanction_count_by_user(
        self,
        user_pk: UUID,
        sanction_type: SanctionType | None = None,
        *,
        active_only: bool = False,
    ) -> int:
        """Get count of sanctions for a user."""
        where_conditions = ["user_pk = $1"]
        params = [user_pk]
        param_count = 1

        if sanction_type:
            param_count += 1
            where_conditions.append(f"type = ${param_count}")
            params.append(sanction_type.value)

        if active_only:
            param_count += 1
            where_conditions.append(f"is_active = ${param_count}")
            params.append(True)

        where_clause = "WHERE " + " AND ".join(where_conditions)

        query = f"""
            SELECT COUNT(*) as count
            FROM sanctions
            {where_clause}
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, *params)
            return record["count"] if record else 0


def get_sanction_repository() -> SanctionRepository:
    """Get sanction repository instance."""
    return SanctionRepository()
