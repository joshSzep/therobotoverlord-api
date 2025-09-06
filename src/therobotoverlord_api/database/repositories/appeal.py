"""Appeal repository for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.appeal import Appeal
from therobotoverlord_api.database.models.appeal import AppealCreate
from therobotoverlord_api.database.models.appeal import AppealEligibility
from therobotoverlord_api.database.models.appeal import AppealRateLimits
from therobotoverlord_api.database.models.appeal import AppealStats
from therobotoverlord_api.database.models.appeal import AppealType
from therobotoverlord_api.database.models.appeal import AppealUpdate
from therobotoverlord_api.database.models.appeal import AppealWithContent
from therobotoverlord_api.database.models.base import AppealStatus
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.repositories.base import BaseRepository


class AppealRepository(BaseRepository[Appeal]):
    """Repository for appeal operations."""

    def __init__(self):
        super().__init__("appeals")

    def _record_to_model(self, record: Record) -> Appeal:
        """Convert database record to Appeal model."""
        return Appeal.model_validate(record)

    async def create_appeal(self, appeal_data: AppealCreate, user_pk: UUID) -> Appeal:
        """Create a new appeal."""
        # Determine sanction_pk and flag_pk based on content_type and content_pk
        sanction_pk = None
        flag_pk = None

        if appeal_data.content_type == ContentType.POST and appeal_data.content_pk:
            if appeal_data.appeal_type == AppealType.SANCTION_APPEAL:
                sanction_pk = appeal_data.content_pk
            else:
                flag_pk = appeal_data.content_pk

        data = {
            "user_pk": user_pk,
            "sanction_pk": sanction_pk,
            "flag_pk": flag_pk,
            "appeal_type": appeal_data.appeal_type.value,
            "appeal_reason": appeal_data.reason,
            "evidence": appeal_data.evidence,
            "status": "pending",
            "submitted_at": datetime.now(UTC),
            "previous_appeals_count": await self._get_user_appeals_count(user_pk),
            "priority_score": await self._calculate_priority_score(
                user_pk,
                appeal_data.appeal_type,
            ),
        }

        return await self.create_from_dict(data)

    async def update_appeal(
        self, appeal_pk: UUID, appeal_data: AppealUpdate
    ) -> Appeal | None:
        """Update an existing appeal."""
        data = appeal_data.model_dump(exclude_unset=True)
        return await self.update_from_dict(appeal_pk, data)

    async def get_user_appeals(
        self,
        user_pk: UUID,
        status: AppealStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AppealWithContent]:
        """Get appeals for a specific user with content details."""
        where_conditions = ["a.user_pk = $1"]
        params: list[str | UUID | int] = [user_pk]
        param_count = 2

        if status:
            where_conditions.append(f"a.status = ${param_count}")
            params.append(status.value)
            param_count += 1

        where_clause = " AND ".join(where_conditions)

        query = f"""
            SELECT
                a.*,
                appellant.username as appellant_username,
                reviewer.username as reviewer_username,
                CASE
                    WHEN a.content_type = 'topic' THEN t.title
                    ELSE NULL
                END as content_title,
                CASE
                    WHEN a.content_type = 'topic' THEN LEFT(t.description, 200)
                    WHEN a.content_type = 'post' THEN LEFT(p.content, 200)
                    WHEN a.content_type = 'private_message' THEN LEFT(pm.content, 200)
                    ELSE NULL
                END as content_text
            FROM appeals a
            JOIN users appellant ON a.appellant_pk = appellant.pk
            LEFT JOIN users reviewer ON a.reviewed_by = reviewer.pk
            LEFT JOIN topics t ON a.content_type = 'topic' AND a.content_pk = t.pk
            LEFT JOIN posts p ON a.content_type = 'post' AND a.content_pk = p.pk
            LEFT JOIN private_messages pm ON a.content_type = 'private_message' AND a.content_pk = pm.pk
            WHERE {where_clause}
            ORDER BY a.submitted_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """

        params.append(limit)
        params.append(offset)

        async with get_db_connection() as connection:
            records = await connection.fetch(query, *params)
            return [AppealWithContent.model_validate(record) for record in records]

    async def get_appeals_queue(
        self,
        status: AppealStatus = AppealStatus.PENDING,
        *,
        priority_order: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AppealWithContent]:
        """Get appeals queue for moderators."""
        order_clause = (
            "ORDER BY a.priority_score DESC, a.submitted_at ASC"
            if priority_order
            else "ORDER BY a.submitted_at ASC"
        )

        query = f"""
            SELECT
                a.*,
                appellant.username as appellant_username,
                reviewer.username as reviewer_username,
                CASE
                    WHEN a.content_type = 'topic' THEN t.title
                    ELSE NULL
                END as content_title,
                CASE
                    WHEN a.content_type = 'topic' THEN LEFT(t.description, 200)
                    WHEN a.content_type = 'post' THEN LEFT(p.content, 200)
                    WHEN a.content_type = 'private_message' THEN LEFT(pm.content, 200)
                    ELSE NULL
                END as content_text
            FROM appeals a
            JOIN users appellant ON a.appellant_pk = appellant.pk
            LEFT JOIN users reviewer ON a.reviewed_by = reviewer.pk
            LEFT JOIN topics t ON a.content_type = 'topic' AND a.content_pk = t.pk
            LEFT JOIN posts p ON a.content_type = 'post' AND a.content_pk = p.pk
            LEFT JOIN private_messages pm ON a.content_type = 'private_message' AND a.content_pk = pm.pk
            WHERE a.status = $1
            {order_clause}
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, status.value, limit, offset)
            return [AppealWithContent.model_validate(record) for record in records]

    async def check_appeal_eligibility(
        self, user_pk: UUID, content_type: ContentType, content_pk: UUID
    ) -> AppealEligibility:
        """Check if user is eligible to appeal specific content."""
        rate_limits = AppealRateLimits()
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get user's loyalty score for bonus appeals
        user_loyalty_query = "SELECT loyalty_score FROM users WHERE pk = $1"

        # Check existing appeals for this content
        content_appeals_query = """
            SELECT COUNT(*) as appeal_count
            FROM appeals
            WHERE appellant_pk = $1 AND content_type = $2 AND content_pk = $3
        """

        # Check daily appeal count
        daily_appeals_query = """
            SELECT COUNT(*) as daily_count
            FROM appeals
            WHERE appellant_pk = $1 AND submitted_at >= $2
        """

        # Check for recent denied appeals (cooldown)
        cooldown_query = """
            SELECT MAX(reviewed_at) as last_denied
            FROM appeals
            WHERE appellant_pk = $1 AND status = 'denied'
            AND reviewed_at > $2
        """

        # Check content age (must be within 7 days of creation/moderation)
        content_age_query = self._get_content_age_query(content_type)

        async with get_db_connection() as connection:
            # Get user loyalty score
            loyalty_record = await connection.fetchrow(user_loyalty_query, user_pk)
            loyalty_score = loyalty_record["loyalty_score"] if loyalty_record else 0

            # Calculate max appeals per day with loyalty bonus
            max_daily = rate_limits.max_appeals_per_day
            for threshold, bonus in rate_limits.loyalty_score_bonus_appeals.items():
                if loyalty_score >= threshold:
                    max_daily += bonus

            # Check all eligibility conditions
            content_appeals = await connection.fetchval(
                content_appeals_query, user_pk, content_type.value, content_pk
            )
            daily_appeals = await connection.fetchval(
                daily_appeals_query, user_pk, today_start
            )

            cooldown_cutoff = now - timedelta(hours=rate_limits.cooldown_hours)
            last_denied = await connection.fetchval(
                cooldown_query, user_pk, cooldown_cutoff
            )

            content_age_valid = await connection.fetchval(
                content_age_query, content_pk, rate_limits.content_age_limit_days
            )

            # Determine eligibility
            if (
                content_appeals is not None
                and content_appeals >= rate_limits.max_appeals_per_content
            ):
                return AppealEligibility(
                    eligible=False,
                    reason="Content has already been appealed",
                    max_appeals_per_day=max_daily,
                    appeals_used_today=daily_appeals or 0,
                )

            if daily_appeals is not None and daily_appeals >= max_daily:
                return AppealEligibility(
                    eligible=False,
                    reason=f"Daily appeal limit reached ({max_daily})",
                    max_appeals_per_day=max_daily,
                    appeals_used_today=daily_appeals or 0,
                )

            if last_denied:
                cooldown_expires = last_denied + timedelta(
                    hours=rate_limits.cooldown_hours
                )
                return AppealEligibility(
                    eligible=False,
                    reason="Appeal cooldown period active",
                    cooldown_expires_at=cooldown_expires,
                    max_appeals_per_day=max_daily,
                    appeals_used_today=daily_appeals or 0,
                )

            if not content_age_valid:
                return AppealEligibility(
                    eligible=False,
                    reason=f"Content is older than {rate_limits.content_age_limit_days} days",
                    max_appeals_per_day=max_daily,
                    appeals_used_today=daily_appeals or 0,
                )

            return AppealEligibility(
                eligible=True,
                appeals_remaining=max_daily - (daily_appeals or 0),
                max_appeals_per_day=max_daily,
                appeals_used_today=daily_appeals or 0,
            )

    async def get_appeal_statistics(self) -> AppealStats:
        """Get appeal statistics for moderators."""
        stats_query = """
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as total_pending,
                COUNT(*) FILTER (WHERE status = 'under_review') as total_under_review,
                COUNT(*) FILTER (WHERE status = 'sustained') as total_sustained,
                COUNT(*) FILTER (WHERE status = 'denied') as total_denied,
                COUNT(*) FILTER (WHERE status = 'withdrawn') as total_withdrawn,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE submitted_at::date = CURRENT_DATE) as total_today,
                AVG(EXTRACT(EPOCH FROM (reviewed_at - submitted_at)) / 3600)
                    FILTER (WHERE reviewed_at IS NOT NULL) as avg_review_hours
            FROM appeals
            WHERE submitted_at > NOW() - INTERVAL '30 days'
        """

        appeals_by_type_query = """
            SELECT appeal_type, COUNT(*) as count
            FROM appeals
            WHERE submitted_at > NOW() - INTERVAL '30 days'
            GROUP BY appeal_type
            ORDER BY count DESC
        """

        top_appellants_query = """
            SELECT
                u.username,
                COUNT(*) as appeal_count
            FROM appeals a
            JOIN users u ON a.appellant_pk = u.pk
            WHERE a.submitted_at > NOW() - INTERVAL '30 days'
            GROUP BY u.pk, u.username
            ORDER BY appeal_count DESC
            LIMIT 10
        """

        reviewer_stats_query = """
            SELECT
                u.username,
                COUNT(*) as reviews_completed,
                COUNT(*) FILTER (WHERE a.status = 'sustained') as total_sustained,
                COUNT(*) FILTER (WHERE a.status = 'denied') as total_denied
            FROM appeals a
            JOIN users u ON a.reviewed_by = u.pk
            WHERE a.reviewed_at > NOW() - INTERVAL '30 days'
            GROUP BY u.pk, u.username
            ORDER BY reviews_completed DESC
            LIMIT 10
        """

        async with get_db_connection() as connection:
            # Get main statistics
            stats_record = await connection.fetchrow(stats_query)

            # Get appeals by type
            type_records = await connection.fetch(appeals_by_type_query)
            appeals_by_type = {
                record["appeal_type"]: record["count"] for record in type_records
            }

            # Get top appellants
            appellant_records = await connection.fetch(top_appellants_query)
            top_appellants = [
                {"username": record["username"], "appeal_count": record["appeal_count"]}
                for record in appellant_records
            ]

            # Get reviewer statistics
            reviewer_records = await connection.fetch(reviewer_stats_query)
            reviewer_stats = [
                {
                    "username": record["username"],
                    "reviews_completed": record["reviews_completed"],
                    "sustained_count": record["total_sustained"],
                    "denied_count": record["total_denied"],
                }
                for record in reviewer_records
            ]

            # Extract values with defaults
            total_pending = stats_record["total_pending"] or 0 if stats_record else 0
            total_under_review = (
                stats_record["total_under_review"] or 0 if stats_record else 0
            )
            total_sustained = (
                stats_record["total_sustained"] or 0 if stats_record else 0
            )
            total_denied = stats_record["total_denied"] or 0 if stats_record else 0
            total_withdrawn = (
                stats_record["total_withdrawn"] or 0 if stats_record else 0
            )
            total_count = stats_record["total_count"] or 0 if stats_record else 0
            total_today = stats_record["total_today"] or 0 if stats_record else 0

            return AppealStats(
                total_pending=total_pending,
                total_under_review=total_under_review,
                total_sustained=total_sustained,
                total_denied=total_denied,
                total_withdrawn=total_withdrawn,
                total_count=total_count,
                total_today=total_today,
                average_review_time_hours=stats_record["avg_review_hours"]
                if stats_record
                else None,
                appeals_by_type=appeals_by_type,
                top_appellants=top_appellants,
                reviewer_stats=reviewer_stats,
            )

    async def count_user_appeals(
        self, user_pk: UUID, status: AppealStatus | None = None
    ) -> int:
        """Count appeals for a user."""
        if status:
            return await self.count(
                "user_pk = $1 AND status = $2", [user_pk, status.value]
            )
        return await self.count("user_pk = $1", [user_pk])

    async def _get_user_appeals_count(self, user_pk: UUID) -> int:
        """Get total number of appeals submitted by user."""
        return await self.count("user_pk = $1", [user_pk])

    async def _calculate_priority_score(
        self, user_pk: UUID, appeal_type: AppealType
    ) -> int:
        """Calculate priority score for appeal based on user loyalty and appeal type."""
        # Get user loyalty score
        query = "SELECT loyalty_score FROM users WHERE pk = $1"

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, user_pk)
            loyalty_score = record["loyalty_score"] if record else 0

        # Base priority by appeal type
        base_priority = {
            AppealType.SANCTION_APPEAL: 100,
            AppealType.CONTENT_RESTORATION: 75,
            AppealType.FLAG_APPEAL: 50,
        }

        # Loyalty multiplier (capped at 5x)
        loyalty_multiplier = min(loyalty_score / 100, 5.0)

        return int(base_priority[appeal_type] * (1 + loyalty_multiplier))

    def _get_content_age_query(self, content_type: ContentType) -> str:
        """Get query to check if content is within appealable age limit."""
        if content_type == ContentType.TOPIC:
            return """
                SELECT EXISTS(
                    SELECT 1 FROM topics
                    WHERE pk = $1 AND created_at > NOW() - INTERVAL '%s days'
                ) as valid
            """
        if content_type == ContentType.POST:
            return """
                SELECT EXISTS(
                    SELECT 1 FROM posts
                    WHERE pk = $1 AND created_at > NOW() - INTERVAL '%s days'
                ) as valid
            """
        if content_type == ContentType.PRIVATE_MESSAGE:
            return """
                SELECT EXISTS(
                    SELECT 1 FROM private_messages
                    WHERE pk = $1 AND sent_at > NOW() - INTERVAL '%s days'
                ) as valid
            """

        return "SELECT FALSE as valid"  # Default to invalid

    async def approve_appeal(
        self, appeal_id: UUID, feedback: str | None = None
    ) -> bool:
        """Approve an appeal."""
        try:
            async with get_db_connection() as connection:
                query = """
                    UPDATE appeals
                    SET status = $1,
                        updated_at = NOW(),
                        moderator_feedback = $2
                    WHERE pk = $3
                    RETURNING pk
                """
                result = await connection.fetchrow(
                    query, AppealStatus.SUSTAINED.value, feedback, appeal_id
                )
                return result is not None
        except Exception:
            return False

    async def reject_appeal(self, appeal_id: UUID, feedback: str | None = None) -> bool:
        """Reject an appeal."""
        try:
            async with get_db_connection() as connection:
                query = """
                    UPDATE appeals
                    SET status = $1,
                        updated_at = NOW(),
                        moderator_feedback = $2
                    WHERE pk = $3
                    RETURNING pk
                """
                result = await connection.fetchrow(
                    query, AppealStatus.DENIED.value, feedback, appeal_id
                )
                return result is not None
        except Exception:
            return False
