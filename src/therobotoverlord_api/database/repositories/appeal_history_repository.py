"""Appeal history repository for database operations."""

from uuid import UUID

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.appeal_history import AppealHistoryAction
from therobotoverlord_api.database.models.appeal_history import AppealHistoryCreate
from therobotoverlord_api.database.models.appeal_history import AppealHistoryEntry
from therobotoverlord_api.database.models.appeal_history import AppealStatusSummary


class AppealHistoryRepository:
    """Repository for appeal history operations."""

    async def create_history_entry(
        self, entry_data: AppealHistoryCreate
    ) -> AppealHistoryEntry:
        """Create a new appeal history entry."""
        async with get_db_connection() as conn:
            query = """
                INSERT INTO appeal_history (
                    appeal_pk, action, actor_pk, details, notes
                ) VALUES ($1, $2, $3, $4, $5)
                RETURNING pk, appeal_pk, action, actor_pk, details, notes, created_at
            """
            record = await conn.fetchrow(
                query,
                entry_data.appeal_pk,
                entry_data.action.value,
                entry_data.actor_pk,
                entry_data.details,
                entry_data.notes,
            )
            return AppealHistoryEntry.model_validate(record)

    async def get_appeal_history(self, appeal_pk: UUID) -> list[AppealHistoryEntry]:
        """Get complete history for an appeal."""
        async with get_db_connection() as conn:
            query = """
                SELECT
                    ah.pk,
                    ah.appeal_pk,
                    ah.action,
                    ah.actor_pk,
                    u.username as actor_username,
                    ah.details,
                    ah.notes,
                    ah.created_at
                FROM appeal_history ah
                LEFT JOIN users u ON ah.actor_pk = u.pk
                WHERE ah.appeal_pk = $1
                ORDER BY ah.created_at ASC
            """
            records = await conn.fetch(query, appeal_pk)
            return [AppealHistoryEntry.model_validate(record) for record in records]

    async def get_user_appeal_history(
        self, user_pk: UUID, limit: int = 50
    ) -> list[AppealHistoryEntry]:
        """Get appeal history for a specific user."""
        async with get_db_connection() as conn:
            query = """
                SELECT
                    ah.pk,
                    ah.appeal_pk,
                    ah.action,
                    ah.actor_pk,
                    u.username as actor_username,
                    ah.details,
                    ah.notes,
                    ah.created_at
                FROM appeal_history ah
                LEFT JOIN users u ON ah.actor_pk = u.pk
                INNER JOIN appeals a ON ah.appeal_pk = a.pk
                WHERE a.appellant_pk = $1
                ORDER BY ah.created_at DESC
                LIMIT $2
            """
            records = await conn.fetch(query, user_pk, limit)
            return [AppealHistoryEntry.model_validate(record) for record in records]

    async def get_appeal_status_summary(
        self, appeal_pk: UUID
    ) -> AppealStatusSummary | None:
        """Get status summary for an appeal."""
        async with get_db_connection() as conn:
            # Get basic appeal info and current status
            appeal_query = """
                SELECT
                    a.pk as appeal_pk,
                    a.status as current_status,
                    a.created_at as submitted_at,
                    a.updated_at as last_updated,
                    u.username as assigned_to
                FROM appeals a
                LEFT JOIN users u ON a.reviewed_by = u.pk
                WHERE a.pk = $1
            """
            appeal_record = await conn.fetchrow(appeal_query, appeal_pk)
            if not appeal_record:
                return None

            # Get history count
            history_count_query = """
                SELECT COUNT(*) as total_entries
                FROM appeal_history
                WHERE appeal_pk = $1
            """
            count_record = await conn.fetchrow(history_count_query, appeal_pk)
            total_entries = count_record["total_entries"] if count_record else 0

            # Get key milestones
            milestones_query = """
                SELECT
                    action,
                    created_at,
                    details,
                    u.username as actor_username
                FROM appeal_history ah
                LEFT JOIN users u ON ah.actor_pk = u.pk
                WHERE ah.appeal_pk = $1
                AND ah.action IN ('submitted', 'assigned', 'sustained', 'denied', 'withdrawn')
                ORDER BY ah.created_at ASC
            """
            milestone_records = await conn.fetch(milestones_query, appeal_pk)

            # Calculate resolution time if resolved
            resolution_time_hours = None
            if appeal_record["current_status"] in ["sustained", "denied"]:
                time_diff = (
                    appeal_record["last_updated"] - appeal_record["submitted_at"]
                )
                resolution_time_hours = time_diff.total_seconds() / 3600

            key_milestones = [
                {
                    "action": record["action"],
                    "timestamp": record["created_at"],
                    "actor": record["actor_username"],
                    "details": record["details"],
                }
                for record in milestone_records
            ]

            return AppealStatusSummary(
                appeal_pk=appeal_record["appeal_pk"],
                current_status=appeal_record["current_status"],
                submitted_at=appeal_record["submitted_at"],
                last_updated=appeal_record["last_updated"],
                assigned_to=appeal_record["assigned_to"],
                resolution_time_hours=resolution_time_hours,
                total_history_entries=total_entries,
                key_milestones=key_milestones,
            )

    async def get_recent_activity(
        self, limit: int = 20, action_filter: list[AppealHistoryAction] | None = None
    ) -> list[AppealHistoryEntry]:
        """Get recent appeal activity across all appeals."""
        async with get_db_connection() as conn:
            where_clause = ""
            params: list[int | list[str]] = [limit]

            if action_filter:
                action_values = [action.value for action in action_filter]
                where_clause = f"WHERE ah.action = ANY(${len(params) + 1})"
                params.append(action_values)

            query = f"""
                SELECT
                    ah.pk,
                    ah.appeal_pk,
                    ah.action,
                    ah.actor_pk,
                    u.username as actor_username,
                    ah.details,
                    ah.notes,
                    ah.created_at
                FROM appeal_history ah
                LEFT JOIN users u ON ah.actor_pk = u.pk
                {where_clause}
                ORDER BY ah.created_at DESC
                LIMIT $1
            """
            records = await conn.fetch(query, *params)
            return [AppealHistoryEntry.model_validate(record) for record in records]

    async def get_moderator_activity(
        self, moderator_pk: UUID, days: int = 30
    ) -> list[AppealHistoryEntry]:
        """Get appeal activity for a specific moderator."""
        async with get_db_connection() as conn:
            query = """
                SELECT
                    ah.pk,
                    ah.appeal_pk,
                    ah.action,
                    ah.actor_pk,
                    u.username as actor_username,
                    ah.details,
                    ah.notes,
                    ah.created_at
                FROM appeal_history ah
                LEFT JOIN users u ON ah.actor_pk = u.pk
                WHERE ah.actor_pk = $1
                AND ah.created_at >= NOW() - INTERVAL '%s days'
                ORDER BY ah.created_at DESC
            """
            records = await conn.fetch(query, moderator_pk, days)
            return [AppealHistoryEntry.model_validate(record) for record in records]
